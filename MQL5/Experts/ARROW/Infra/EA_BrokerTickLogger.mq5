//+------------------------------------------------------------------+
//|                                        EA_BrokerTickLogger.mq5   |
//|                                                    ARROW project |
//+------------------------------------------------------------------+
//
// Coleta continua dos ticks reais do broker para `data/broker/`.
//
// ESTE EA NUNCA NEGOCIA. Ver a secao "Prova de que nao negocia" abaixo.
//
// POR QUE EXPERT ADVISOR E NAO SCRIPT (ADR 0008)
//   A versao anterior era Script e morreu duas vezes em 24 horas, por dois
//   mecanismos diferentes:
//
//     2026-08-02  reinicio do terminal      -> Script nao sobrevive
//     2026-08-02  DataAudit no mesmo grafico -> um Script por grafico; o
//                                               segundo desaloja o primeiro
//
//   E havia um terceiro esperando: trocar o timeframe do grafico tambem mata
//   um Script.
//
//   Um EA nao tem nenhum dos tres. Reanexa sozinho quando o terminal sobe,
//   convive com scripts no mesmo grafico, e sobrevive a troca de timeframe
//   (OnDeinit/OnInit com REASON_CHARTCHANGE, retomando do arquivo). Alem
//   disso ele APARECE no canto do grafico, entao da para saber que esta vivo
//   sem ler log.
//
// DIAGNOSTICABILIDADE
//   A licao concreta do incidente e que a morte foi silenciosa: o Script
//   escreveu "parado" e ninguem viu. Este EA registra o MOTIVO da parada em
//   OnDeinit, com o codigo traduzido, e emite batimento periodico com quantos
//   ticks gravou. Uma coleta que morre tem de deixar rastro legivel.
//
// ONDE ESCREVE
//   Sandbox `<terminal>\MQL5\Files\`, e a junction `Files\ARROW` -> repo/data
//   (tools/setup/junctions.ps1) faz "ARROW\broker\..." aterrissar dentro do
//   projeto. Sem a junction o EA RECUSA iniciar, em vez de gravar na pasta do
//   terminal e fingir que funcionou.
//
// FUSO
//   `MqlTick.time_msc` esta em hora de servidor. A secao 10.7 mediu servidor =
//   UTC com relogio fixo, por duas rotas independentes. O offset e medido
//   assim mesmo a cada verificacao e registrado em `_offset_log.csv`: se a
//   premissa cair, a conversao e refeita a partir do registro em vez de o
//   historico ser descartado.
//
// PROVA DE QUE NAO NEGOCIA
//   Este arquivo nao contem, e nao deve conter, nenhuma das seguintes:
//   OrderSend, PositionOpen, PositionClose, PositionModify, Buy, Sell,
//   CTrade, MqlTradeRequest. A ausencia e verificavel por busca textual, e o
//   `run` da sessao registra que a busca foi feita. Um coletor que possa
//   emitir ordem por acidente e um risco que nao precisa existir.
//
#property copyright "ARROW"
#property version   "1.00"
#property description "Coleta continua de ticks reais para data/broker/. NAO NEGOCIA."

//--- entradas ---------------------------------------------------------------
//
// InpSymbol NAO herda o simbolo do grafico. Solto num grafico de BTCUSDm, a
// versao anterior coletou BTCUSDm em silencio por uma hora. O projeto e
// XAUUSD e nada mais (secao 14, ADR 0007), e data/broker/ e definido como
// ticks do XAUUSDm (ADR 0005).
input string InpSymbol        = "XAUUSDm";  // Simbolo (NAO herda do grafico)
input int    InpPollMs        = 250;        // Intervalo de coleta (ms)
input int    InpHeartbeatMin  = 30;         // Batimento no log (min, 0 = off)
input bool   InpBackfill      = false;      // Puxar historico retido ao iniciar
input int    InpBackfillDays  = 7;          // Dias de historico a puxar

//--- constantes -------------------------------------------------------------
#define ARROW_DIR    "ARROW\\broker"
#define OFFSET_LOG   "ARROW\\broker\\_offset_log.csv"
#define CSV_HEADER   "ts,bid,ask,bid_vol,ask_vol"

//--- estado -----------------------------------------------------------------
string   g_symbol      = "";
int      g_digits      = 3;
long     g_last_msc    = 0;   // time_msc do ultimo tick GRAVADO (hora de servidor)
int      g_dup_at_last = 0;   // quantos ticks nesse mesmo ms ja foram gravados
string   g_cur_file    = "";
long     g_offset_sec  = 0;   // servidor - UTC, em segundos
long     g_written     = 0;   // ticks gravados nesta execucao
datetime g_started     = 0;
datetime g_last_beat   = 0;
datetime g_last_offchk = 0;

//+------------------------------------------------------------------+
//| Offset servidor->UTC, arredondado para o minuto.                 |
//+------------------------------------------------------------------+
long MeasureOffsetSec()
{
   long raw = (long)TimeTradeServer() - (long)TimeGMT();
   return((long)MathRound((double)raw / 60.0) * 60);
}

//+------------------------------------------------------------------+
//| Instante UTC em ISO com milissegundos: "2026-08-03 07:01:33.482" |
//+------------------------------------------------------------------+
string FormatUtcMsc(const long utc_msc)
{
   datetime    secs = (datetime)(utc_msc / 1000);
   int         ms   = (int)(utc_msc % 1000);
   MqlDateTime dt;
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
   FileWriteString(h, StringFormat("%s,%d,%s\r\n",
                                   FormatUtcMsc(((long)TimeGMT()) * 1000),
                                   (int)offset_sec, source));
   FileClose(h);
}

//+------------------------------------------------------------------+
//| Arquivo de dia mais recente ja gravado para este simbolo.        |
//|                                                                  |
//| Procurar pelo mais recente, e nao pela data de hoje, porque os   |
//| arquivos sao nomeados pela data do TICK. Com o mercado fechado as |
//| duas divergem, e a busca por data de parede falha -- o que fazia  |
//| o script regravar o ultimo tick a cada reinicio de fim de semana. |
//+------------------------------------------------------------------+
string FindLatestDayFile()
{
   string filter = ARROW_DIR + "\\" + g_symbol + "-*.csv";
   string found  = "";
   long   h = FileFindFirst(filter, found);
   if(h == INVALID_HANDLE)
      return("");

   string best = "";
   do
   {
      string name  = found;
      int    slash = StringFind(name, "\\");
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
//| Varre um arquivo de dia existente para retomar sem duplicar.     |
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
      if(StringLen(line) == 0)          continue;
      if(StringFind(line, "ts,") == 0)  continue;
      int comma = StringFind(line, ",");
      if(comma <= 0)                    continue;

      string ts = StringSubstr(line, 0, comma);
      if(ts == last_ts) run++;
      else { last_ts = ts; run = 1; }
   }
   FileClose(h);
   if(last_ts == "")
      return(false);

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
      long   utc_msc = ticks[i].time_msc - (g_offset_sec * 1000);
      string fname   = DayFileName(utc_msc);

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

      // bid_vol/ask_vol = 0: o broker nao fornece volume por lado. As colunas
      // existem so para compatibilidade de esquema com raw/ (ADR 0005). Nao
      // sao dado ausente a imputar, sao dado inexistente.
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
//| Coleta o que houver desde o ultimo tick gravado.                 |
//+------------------------------------------------------------------+
void Collect()
{
   static MqlTick ticks[];
   int got = CopyTicks(g_symbol, ticks, COPY_TICKS_INFO, (ulong)g_last_msc, 0);
   if(got <= 0)
      return;

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

//+------------------------------------------------------------------+
//| Backfill do historico ainda retido pelo broker.                  |
//+------------------------------------------------------------------+
void Backfill()
{
   LogOffset(MeasureOffsetSec(), "backfill");

   ulong from_msc = ((ulong)(TimeTradeServer() - InpBackfillDays * 86400)) * 1000;
   MqlTick ticks[];
   int got = CopyTicksRange(g_symbol, ticks, COPY_TICKS_INFO, from_msc,
                            (ulong)TimeTradeServer() * 1000);
   if(got <= 0)
   {
      PrintFormat("ARROW: backfill nao retornou ticks (erro %d). O broker pode nao reter esse periodo.",
                  GetLastError());
      return;
   }

   PrintFormat("ARROW: backfill trouxe %d ticks dos ultimos %d dias.", got, InpBackfillDays);
   Print("ARROW: ATENCAO — o backfill pode atravessar fronteira de DST. ",
         "O offset usado esta marcado como 'backfill' em _offset_log.csv.");

   int start = got;
   for(int i = 0; i < got; i++)
      if(ticks[i].time_msc > g_last_msc) { start = i; break; }
   if(start < got)
      WriteTicks(ticks, start, got);
}

//+------------------------------------------------------------------+
//| Traduz o codigo de desinicializacao.                             |
//|                                                                  |
//| Existe porque a morte anterior foi silenciosa: o Script escreveu  |
//| "parado" e ninguem soube por que. Uma coleta que morre tem de     |
//| deixar rastro legivel.                                           |
//+------------------------------------------------------------------+
string DeinitReasonText(const int reason)
{
   switch(reason)
   {
      case REASON_PROGRAM:     return("o proprio EA pediu parada");
      case REASON_REMOVE:      return("REMOVIDO DO GRAFICO por operador");
      case REASON_RECOMPILE:   return("recompilado — reanexa sozinho");
      case REASON_CHARTCHANGE: return("simbolo ou periodo do grafico mudou — reanexa sozinho");
      case REASON_CHARTCLOSE:  return("GRAFICO FECHADO");
      case REASON_PARAMETERS:  return("parametros alterados — reanexa sozinho");
      case REASON_ACCOUNT:     return("conta trocada — reanexa sozinho");
      case REASON_TEMPLATE:    return("template do grafico trocado");
      case REASON_INITFAILED:  return("OnInit devolveu erro");
      case REASON_CLOSE:       return("TERMINAL FECHADO — reanexa quando subir");
      default:                 return("motivo desconhecido " + IntegerToString(reason));
   }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   g_symbol = InpSymbol;
   g_written = 0;
   g_started = TimeGMT();

   if(!SymbolSelect(g_symbol, true))
   {
      PrintFormat("ARROW: simbolo %s indisponivel. Abortando.", g_symbol);
      return(INIT_FAILED);
   }
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);

   if(!CheckWritePath())
      return(INIT_FAILED);

   g_offset_sec  = MeasureOffsetSec();
   g_last_offchk = TimeGMT();
   LogOffset(g_offset_sec, "live");

   PrintFormat("ARROW EA_BrokerTickLogger v1.00: %s, digits=%d, offset servidor-UTC = %d s",
               g_symbol, g_digits, (int)g_offset_sec);

   if(g_symbol != _Symbol)
      PrintFormat("ARROW: nota — o grafico e %s e a coleta e %s. Correto: o simbolo NAO herda do grafico.",
                  _Symbol, g_symbol);

   // Retomada: pelo arquivo mais recente do simbolo, nao pela data de hoje.
   string latest = FindLatestDayFile();
   long   rmsc = 0;
   int    rdup = 0;
   if(latest != "" && ScanFileTail(latest, rmsc, rdup))
   {
      g_last_msc    = rmsc;
      g_dup_at_last = rdup;
      PrintFormat("ARROW: retomando %s — ultimo tick em %s (%d no mesmo ms).",
                  latest, FormatUtcMsc(g_last_msc - g_offset_sec * 1000), g_dup_at_last);
   }
   else
   {
      Print("ARROW: nenhum arquivo anterior — comecando do tick corrente.");
      MqlTick t;
      if(SymbolInfoTick(g_symbol, t))
      {
         g_last_msc    = t.time_msc;
         g_dup_at_last = 0;
      }
   }

   if(InpBackfill)
      Backfill();

   // O timer, e nao o OnTick, e o motor da coleta: OnTick so dispara para o
   // simbolo DO GRAFICO, e o EA precisa funcionar em qualquer grafico. OnTick
   // fica como acelerador quando os dois coincidem.
   if(!EventSetMillisecondTimer(InpPollMs))
   {
      PrintFormat("ARROW: EventSetMillisecondTimer falhou (erro %d)", GetLastError());
      return(INIT_FAILED);
   }

   g_last_beat = TimeGMT();
   Print("ARROW: coletando. O EA sobrevive a reinicio do terminal e convive com scripts.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   PrintFormat("ARROW: PARANDO — %s. %d ticks gravados desde %s. Ultimo arquivo: %s",
               DeinitReasonText(reason), (int)g_written,
               TimeToString(g_started, TIME_DATE|TIME_MINUTES),
               (g_cur_file == "" ? "(nenhum)" : g_cur_file));

   if(reason == REASON_REMOVE || reason == REASON_CHARTCLOSE)
      Print("ARROW: ATENCAO — parada DEFINITIVA. A coleta NAO reinicia sozinha. ",
            "Cada hora parada e verdade de campo perdida para sempre.");
}

//+------------------------------------------------------------------+
//| Timer — motor da coleta                                          |
//+------------------------------------------------------------------+
void OnTimer()
{
   Collect();

   datetime agora = TimeGMT();

   // O offset pode mudar. Reconferir de hora em hora e registrar toda mudanca,
   // em vez de assumir que e constante.
   if((long)(agora - g_last_offchk) > 3600)
   {
      long novo = MeasureOffsetSec();
      if(novo != g_offset_sec)
      {
         PrintFormat("ARROW: offset servidor-UTC mudou de %d s para %d s.",
                     (int)g_offset_sec, (int)novo);
         g_offset_sec = novo;
         LogOffset(g_offset_sec, "live");
      }
      g_last_offchk = agora;
   }

   // Batimento: um coletor vivo tem de ser distinguivel de um coletor morto
   // sem que ninguem precise abrir o CSV.
   if(InpHeartbeatMin > 0 && (long)(agora - g_last_beat) >= InpHeartbeatMin * 60)
   {
      PrintFormat("ARROW: vivo. %d ticks nesta execucao. Ultimo arquivo: %s",
                  (int)g_written, (g_cur_file == "" ? "(nenhum ainda)" : g_cur_file));
      g_last_beat = agora;
   }
}

//+------------------------------------------------------------------+
//| Tick do grafico — acelerador, nao o motor                        |
//+------------------------------------------------------------------+
void OnTick()
{
   Collect();
}
//+------------------------------------------------------------------+
