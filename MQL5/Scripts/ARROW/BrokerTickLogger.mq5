//+------------------------------------------------------------------+
//|                                            BrokerTickLogger.mq5  |
//|                                                    ARROW project |
//+------------------------------------------------------------------+
//
// Coleta contínua dos ticks reais do broker para `data/broker/`.
//
// POR QUE ESTE SCRIPT É URGENTE
//   `data/broker/` é o único insumo do modelo de spread (ADR 0005), e o modelo
//   de spread é pré-requisito de `curated/`, que é pré-requisito de `bars/`.
//   O broker retém pouco histórico de tick e a janela rola: cada dia não
//   coletado é verdade de campo perdida para sempre.
//
// ONDE ELE ESCREVE
//   O MQL5 é confinado ao sandbox `<terminal>\MQL5\Files\`. A junction
//   `Files\ARROW` -> `C:\dev\ARROW\data`, criada por tools/setup/junctions.ps1,
//   faz o caminho relativo "ARROW\broker\..." aterrissar dentro do repositório.
//   Sem a junction o dado fica preso na pasta do terminal — o script detecta
//   isso e recusa iniciar.
//
// FUSO — LEIA ANTES DE MEXER
//   `MqlTick.time_msc` está em HORA DO SERVIDOR. O projeto grava tudo em UTC
//   (CLAUDE.md §10.3). A conversão usa o offset medido por
//   `TimeTradeServer() - TimeGMT()`.
//
//   Esse offset é CORRETO para o instante em que é medido, e é exatamente por
//   isso que ele serve aqui: cada tick ao vivo é convertido com o offset
//   vigente no momento em que chega. O que ele NÃO responde é se o servidor
//   observa DST — para isso é preciso o método da §10.7, com âncora em duas
//   estações. Por isso todo offset aplicado é registrado em `_offset_log.csv`:
//   se a §10.7 concluir algo que contradiga o que foi assumido, a conversão é
//   refeita a partir do registro, sem perda.
//
//   Consequência dura: o backfill histórico atravessa fronteiras de DST em
//   potencial, então ele é OPCIONAL, desligado por padrão, e o offset usado
//   fica marcado como `backfill` no log — nunca misturado com `live`.
//
// ESQUEMA DO CSV — igual ao de `raw/` (ADR 0005 §2)
//   ts,bid,ask,bid_vol,ask_vol
//
//   LIMITAÇÃO CONHECIDA: o broker não fornece volume por lado. `bid_vol` e
//   `ask_vol` são gravados como 0 e existem apenas para compatibilidade de
//   esquema com `raw/`. Não são dado ausente a imputar — são dado inexistente.
//   Nenhuma análise deve tratá-los como volume.
//
#property copyright "ARROW"
#property version   "1.00"
#property script_show_inputs
#property description "Coleta continua de ticks reais para data/broker/. Manter rodando."

//--- entradas ---------------------------------------------------------------
//
// InpSymbol NAO herda o simbolo do grafico, e isso e deliberado.
//
// A versao anterior usava "" -> _Symbol, e o resultado foi previsivel: solto
// num grafico de BTCUSDm, o script coletou BTCUSDm em silencio por uma hora.
// O projeto e XAUUSD M1 e nada mais (CLAUDE.md secao 14), data/broker/ e
// definido como ticks do XAUUSDm (ADR 0005), e um arquivo de outro instrumento
// ali dentro envenena o modelo de spread sem levantar erro nenhum.
//
// O script le tick por SIMBOLO, nao por grafico. Nao ha motivo para depender de
// onde ele foi solto.
input string InpSymbol       = "XAUUSDm";  // Simbolo (NAO herda do grafico)
input int    InpPollMs       = 250;    // Intervalo de coleta (ms)
input bool   InpBackfill     = false;  // Puxar historico retido ao iniciar
input int    InpBackfillDays = 7;      // Quantos dias de historico puxar

//--- constantes -------------------------------------------------------------
#define ARROW_DIR    "ARROW\\broker"
#define OFFSET_LOG   "ARROW\\broker\\_offset_log.csv"
#define CSV_HEADER   "ts,bid,ask,bid_vol,ask_vol"

//--- estado -----------------------------------------------------------------
string g_symbol      = "";
int    g_digits      = 3;
long   g_last_msc    = 0;   // time_msc do ultimo tick GRAVADO (hora do servidor)
int    g_dup_at_last = 0;   // quantos ticks com esse mesmo time_msc ja foram gravados
string g_cur_file    = "";  // arquivo do dia atualmente aberto
long   g_offset_sec  = 0;   // servidor - UTC, em segundos
long   g_written     = 0;

//+------------------------------------------------------------------+
//| Offset servidor->UTC, arredondado para o minuto.                 |
//|                                                                  |
//| Arredondar remove o jitter de sub-segundo entre as duas leituras |
//| sem mascarar nada: offsets de fuso reais sao multiplos de 15 min.|
//+------------------------------------------------------------------+
long MeasureOffsetSec()
{
   long raw = (long)TimeTradeServer() - (long)TimeGMT();
   long rounded = (long)MathRound((double)raw / 60.0) * 60;
   return(rounded);
}

//+------------------------------------------------------------------+
//| Formata um instante UTC em ISO com milissegundos.                |
//| Saida: "2026-08-02 07:41:33.482" — parseavel direto pelo pandas. |
//+------------------------------------------------------------------+
string FormatUtcMsc(const long utc_msc)
{
   datetime      secs = (datetime)(utc_msc / 1000);
   int           ms   = (int)(utc_msc % 1000);
   MqlDateTime   dt;
   TimeToStruct(secs, dt);

   return(StringFormat("%04d-%02d-%02d %02d:%02d:%02d.%03d",
                       dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec, ms));
}

//+------------------------------------------------------------------+
//| Nome do arquivo do dia, pela data UTC do tick.                   |
//+------------------------------------------------------------------+
string DayFileName(const long utc_msc)
{
   MqlDateTime dt;
   TimeToStruct((datetime)(utc_msc / 1000), dt);
   return(StringFormat("%s\\%s-%04d%02d%02d.csv",
                       ARROW_DIR, g_symbol, dt.year, dt.mon, dt.day));
}

//+------------------------------------------------------------------+
//| Registra o offset aplicado, para auditoria posterior.            |
//|                                                                  |
//| Existe porque a hipotese de fuso da §10.7 ainda nao foi          |
//| confirmada. Se ela for refutada, este log e o que permite        |
//| reconverter o historico ja gravado em vez de descarta-lo.        |
//+------------------------------------------------------------------+
void LogOffset(const long offset_sec, const string source)
{
   bool fresh = !FileIsExist(OFFSET_LOG);
   int  h = FileOpen(OFFSET_LOG, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consegui abrir %s (erro %d)", OFFSET_LOG, GetLastError());
      return;
   }
   FileSeek(h, 0, SEEK_END);
   if(fresh)
      FileWriteString(h, "measured_at_utc,offset_seconds,source\r\n");

   long now_utc_msc = ((long)TimeGMT()) * 1000;
   FileWriteString(h, StringFormat("%s,%d,%s\r\n",
                                   FormatUtcMsc(now_utc_msc), (int)offset_sec, source));
   FileClose(h);
}

//+------------------------------------------------------------------+
//| Arquivo de dia mais recente ja gravado para este simbolo.        |
//|                                                                  |
//| POR QUE NAO BASTA OLHAR A DATA DE HOJE                           |
//|   Os arquivos sao nomeados pela data do TICK; a retomada, na      |
//|   versao anterior, procurava pela data de PAREDE. Enquanto o      |
//|   mercado esta aberto os dois coincidem e nada aparece. Com o     |
//|   mercado fechado eles divergem: num domingo, o ultimo tick e de  |
//|   sexta, entao a busca por XAUUSDm-<domingo>.csv falha, o script  |
//|   conclui que nao ha de onde retomar, e regrava o tick de sexta   |
//|   dentro de XAUUSDm-<sexta>.csv. Um restart no fim de semana --   |
//|   exatamente quando o script e instalado -- duplicava uma linha   |
//|   por vez, em silencio.                                          |
//|                                                                  |
//|   Procurar o arquivo mais recente do simbolo nao depende de o     |
//|   mercado estar aberto. O nome AAAAMMDD ordena lexicograficamente,|
//|   entao o maior nome e o dia mais recente.                       |
//+------------------------------------------------------------------+
string FindLatestDayFile()
{
   string filter = ARROW_DIR + "\\" + g_symbol + "-*.csv";
   string found  = "";

   long h = FileFindFirst(filter, found);
   if(h == INVALID_HANDLE)
      return("");

   string best = "";
   do
   {
      // Conforme o caso, o MQL5 devolve o nome com ou sem o subdiretorio.
      // Normalizar para comparar so o nome do arquivo.
      string name = found;
      int slash = StringFind(name, "\\");
      while(slash >= 0)
      {
         name  = StringSubstr(name, slash + 1);
         slash = StringFind(name, "\\");
      }
      if(StringCompare(name, best) > 0)
         best = name;
   }
   while(FileFindNext(h, found));
   FileFindClose(h);

   if(best == "")
      return("");

   return(ARROW_DIR + "\\" + best);
}

//+------------------------------------------------------------------+
//| Varre um arquivo de dia ja existente para retomar sem duplicar.  |
//|                                                                  |
//| Devolve, pelo ultimo timestamp presente no arquivo: o time_msc   |
//| do servidor e quantas linhas carregam exatamente esse instante.  |
//| A contagem e o que impede duplicata quando varios ticks caem no  |
//| mesmo milissegundo — sem ela, CopyTicks(from=last) reescreveria  |
//| todos eles a cada reinicio.                                      |
//+------------------------------------------------------------------+
bool ScanFileTail(const string fname, long &out_last_msc, int &out_dup)
{
   out_last_msc = 0;
   out_dup      = 0;

   if(!FileIsExist(fname))
      return(false);

   int h = FileOpen(fname, FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consegui ler %s para retomar (erro %d)", fname, GetLastError());
      return(false);
   }

   string last_ts = "";
   int    run     = 0;

   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      if(StringLen(line) == 0)
         continue;
      if(StringFind(line, "ts,") == 0)     // cabecalho
         continue;

      int comma = StringFind(line, ",");
      if(comma <= 0)
         continue;

      string ts = StringSubstr(line, 0, comma);
      if(ts == last_ts)
         run++;
      else
      {
         last_ts = ts;
         run     = 1;
      }
   }
   FileClose(h);

   if(last_ts == "")
      return(false);

   // "2026-08-02 07:41:33.482" -> volta para time_msc de SERVIDOR, que e o
   // dominio em que CopyTicks trabalha.
   string date_part = StringSubstr(last_ts, 0, 10);
   string time_part = StringSubstr(last_ts, 11, 8);
   string ms_part   = StringSubstr(last_ts, 20, 3);

   StringReplace(date_part, "-", ".");
   datetime utc_sec = StringToTime(date_part + " " + time_part);

   out_last_msc = (((long)utc_sec + g_offset_sec) * 1000) + (long)StringToInteger(ms_part);
   out_dup      = run;
   return(true);
}

//+------------------------------------------------------------------+
//| Grava um lote de ticks, abrindo/rolando o arquivo do dia.        |
//+------------------------------------------------------------------+
void WriteTicks(MqlTick &ticks[], const int from_idx, const int count)
{
   for(int i = from_idx; i < count; i++)
   {
      long utc_msc = ticks[i].time_msc - (g_offset_sec * 1000);
      string fname = DayFileName(utc_msc);

      bool fresh = !FileIsExist(fname);
      int  h = FileOpen(fname, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
      if(h == INVALID_HANDLE)
      {
         PrintFormat("ARROW: falha ao abrir %s (erro %d) — parando para nao perder dado em silencio",
                     fname, GetLastError());
         return;
      }
      FileSeek(h, 0, SEEK_END);
      if(fresh)
      {
         FileWriteString(h, CSV_HEADER + "\r\n");
         PrintFormat("ARROW: novo arquivo de dia %s", fname);
      }

      // bid_vol/ask_vol = 0: o broker nao fornece volume por lado. Ver cabecalho.
      FileWriteString(h, StringFormat("%s,%.*f,%.*f,0,0\r\n",
                                      FormatUtcMsc(utc_msc),
                                      g_digits, ticks[i].bid,
                                      g_digits, ticks[i].ask));
      FileClose(h);

      if(ticks[i].time_msc == g_last_msc)
         g_dup_at_last++;
      else
      {
         g_last_msc    = ticks[i].time_msc;
         g_dup_at_last = 1;
      }
      g_cur_file = fname;
      g_written++;
   }
}

//+------------------------------------------------------------------+
//| Verifica que a junction de escrita existe.                       |
//|                                                                  |
//| Sem ela o script "funciona" e grava na pasta do terminal, fora do|
//| projeto — falha silenciosa, exatamente a classe que este projeto |
//| trata como inaceitavel. Melhor recusar iniciar.                  |
//+------------------------------------------------------------------+
bool CheckWritePath()
{
   string probe = ARROW_DIR + "\\_write_probe.tmp";
   int h = FileOpen(probe, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consigo escrever em %s (erro %d).", ARROW_DIR, GetLastError());
      Print("ARROW: rode tools/setup/junctions.ps1 — falta a junction Files\\ARROW -> data.");
      return(false);
   }
   FileClose(h);
   FileDelete(probe);
   return(true);
}

//+------------------------------------------------------------------+
//| Backfill do historico ainda retido pelo broker.                  |
//+------------------------------------------------------------------+
void Backfill()
{
   long offset_bf = MeasureOffsetSec();
   LogOffset(offset_bf, "backfill");

   datetime from_sec = TimeTradeServer() - (InpBackfillDays * 86400);
   ulong    from_msc = ((ulong)from_sec) * 1000;

   MqlTick ticks[];
   int got = CopyTicksRange(g_symbol, ticks, COPY_TICKS_INFO, from_msc, (ulong)TimeTradeServer() * 1000);

   if(got <= 0)
   {
      PrintFormat("ARROW: backfill nao retornou ticks (erro %d). O broker pode nao reter esse periodo.",
                  GetLastError());
      return;
   }

   PrintFormat("ARROW: backfill trouxe %d ticks dos ultimos %d dias.", got, InpBackfillDays);
   Print("ARROW: ATENCAO — o backfill pode atravessar fronteira de DST. ",
         "O offset usado esta marcado como 'backfill' em _offset_log.csv.");

   int start = 0;
   for(int i = 0; i < got; i++)
   {
      if(ticks[i].time_msc > g_last_msc)
      {
         start = i;
         break;
      }
      start = got;   // tudo antigo
   }
   if(start < got)
      WriteTicks(ticks, start, got);
}

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
   g_symbol = (InpSymbol == "") ? _Symbol : InpSymbol;

   if(!SymbolSelect(g_symbol, true))
   {
      PrintFormat("ARROW: simbolo %s indisponivel. Abortando.", g_symbol);
      return;
   }
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);

   if(!CheckWritePath())
      return;

   g_offset_sec = MeasureOffsetSec();
   LogOffset(g_offset_sec, "live");

   PrintFormat("ARROW BrokerTickLogger: %s, digits=%d, offset servidor-UTC = %d s (%.1f h)",
               g_symbol, g_digits, (int)g_offset_sec, g_offset_sec / 3600.0);

   // O projeto e XAUUSD M1 e nada mais (secao 14). Coletar outro instrumento
   // nao e erro de execucao, entao nao aborta -- mas nao pode passar calado,
   // porque o arquivo resultante fica indistinguivel dos legitimos em
   // data/broker/ e envenena o modelo de spread.
   if(g_symbol != "XAUUSDm")
      PrintFormat("ARROW: ATENCAO — %s NAO e XAUUSDm. data/broker/ e definido como ticks do "
                  "XAUUSDm (ADR 0005) e o projeto exclui outros instrumentos (secao 14). "
                  "Remova este script do grafico se isso nao foi intencional.", g_symbol);

   // --- retomada: continuar do arquivo mais recente, aberto ou fechado ------
   string latest     = FindLatestDayFile();
   long   resume_msc = 0;
   int    resume_dup = 0;

   if(latest != "" && ScanFileTail(latest, resume_msc, resume_dup))
   {
      g_last_msc    = resume_msc;
      g_dup_at_last = resume_dup;
      PrintFormat("ARROW: retomando %s — ultimo tick gravado em %s (%d no mesmo ms).",
                  latest, FormatUtcMsc(g_last_msc - g_offset_sec * 1000), g_dup_at_last);
   }
   else
   {
      Print("ARROW: nenhum arquivo anterior para este simbolo — comecando do tick corrente.");
      MqlTick t;
      if(SymbolInfoTick(g_symbol, t))
      {
         g_last_msc    = t.time_msc;
         g_dup_at_last = 0;
      }
   }

   if(InpBackfill)
      Backfill();

   // --- laco de coleta ------------------------------------------------------
   Print("ARROW: coletando. Remover o script do grafico para parar.");

   long last_offset_check = (long)TimeGMT();
   MqlTick ticks[];

   while(!IsStopped())
   {
      // O offset pode mudar (DST do servidor). Reconferir de hora em hora e
      // registrar toda mudanca, em vez de assumir que e constante.
      if(((long)TimeGMT() - last_offset_check) > 3600)
      {
         long now_off = MeasureOffsetSec();
         if(now_off != g_offset_sec)
         {
            PrintFormat("ARROW: offset servidor-UTC mudou de %d s para %d s.",
                        (int)g_offset_sec, (int)now_off);
            g_offset_sec = now_off;
            LogOffset(g_offset_sec, "live");
         }
         last_offset_check = (long)TimeGMT();
      }

      int got = CopyTicks(g_symbol, ticks, COPY_TICKS_INFO, (ulong)g_last_msc, 0);
      if(got > 0)
      {
         // CopyTicks a partir de `from` e INCLUSIVO. Pular os ticks desse mesmo
         // milissegundo que ja foram gravados — e so eles.
         int skip = 0;
         while(skip < got && ticks[skip].time_msc == g_last_msc && skip < g_dup_at_last)
            skip++;
         while(skip < got && ticks[skip].time_msc < g_last_msc)
            skip++;

         if(skip < got)
            WriteTicks(ticks, skip, got);
      }

      Sleep(InpPollMs);
   }

   PrintFormat("ARROW: parado. %d ticks gravados nesta execucao. Ultimo arquivo: %s",
               (int)g_written, g_cur_file);
}
//+------------------------------------------------------------------+
