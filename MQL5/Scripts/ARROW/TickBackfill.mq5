//+------------------------------------------------------------------+
//|                                              TickBackfill.mq5    |
//|                                                    ARROW project |
//+------------------------------------------------------------------+
//
// Puxa o historico de tick real que o broker ainda retem, para medir o
// GAP DE FONTE da secao 11.2 -- Dukascopy contra Exness no mesmo periodo.
//
// POR QUE E SCRIPT E NAO EA
//   Roda uma vez e termina. O ADR 0008 converteu o COLETOR CONTINUO em EA
//   porque ele precisa permanecer vivo; este aqui e o caso oposto, e Script
//   e o artefato certo. E como o EA_BrokerTickLogger e EA, soltar este
//   Script no mesmo grafico NAO o desaloja.
//
// ONDE ESCREVE
//   data/broker_hist/ , separado de data/broker/. Ao vivo e backfill nao se
//   misturam: o ao vivo tem offset medido no instante de cada tick, o
//   historico tem offset medido agora e aplicado retroativamente.
//
// FUSO -- POR QUE ISTO E SEGURO AQUI
//   A secao 10.7 mediu que o relogio do servidor e FIXO e igual a UTC. O que
//   desliza com o DST americano e o CRONOGRAMA DE SESSAO, nao o relogio.
//   Entao converter tick historico com um offset constante esta correto mesmo
//   atravessando fronteira de DST -- que era a ressalva do backfill do EA.
//
#property copyright "ARROW"
#property version   "1.00"
#property script_show_inputs
#property description "Puxa historico de tick real do broker para data/broker_hist/. Nao negocia."

input string InpSymbol   = "XAUUSDm";      // Simbolo
input string InpDataIni  = "2026.07.01";   // Inicio (AAAA.MM.DD, hora de servidor)
input string InpDataFim  = "2026.08.01";   // Fim (exclusivo)
input int    InpTentativas = 30;           // Tentativas por dia enquanto o terminal baixa

#define OUT_DIR    "ARROW\\broker_hist"
#define CSV_HEADER "ts,bid,ask,bid_vol,ask_vol"

int    g_digits     = 3;
long   g_offset_sec = 0;

//+------------------------------------------------------------------+
long MeasureOffsetSec()
{
   long raw = (long)TimeTradeServer() - (long)TimeGMT();
   return((long)MathRound((double)raw / 60.0) * 60);
}

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
//| Um dia de ticks. Devolve quantos gravou, ou -1 se falhou.        |
//|                                                                  |
//| CopyTicksRange devolve -1 enquanto o terminal ainda esta baixando |
//| o historico do servidor. Nao e erro: e para tentar de novo. Sem   |
//| o laco, o primeiro dia sai vazio e o resto parece funcionar.      |
//+------------------------------------------------------------------+
int PuxarDia(const datetime dia_ini, const string fname)
{
   ulong de  = ((ulong)dia_ini) * 1000;
   ulong ate = ((ulong)(dia_ini + 86400)) * 1000;

   MqlTick ticks[];
   int got = -1;
   for(int t = 0; t < InpTentativas; t++)
   {
      got = CopyTicksRange(InpSymbol, ticks, COPY_TICKS_INFO, de, ate);
      if(got >= 0)
         break;
      int err = GetLastError();
      if(t == 0)
         PrintFormat("ARROW: %s — terminal baixando historico (erro %d), aguardando...",
                     TimeToString(dia_ini, TIME_DATE), err);
      ResetLastError();
      Sleep(2000);
   }
   if(got < 0)
   {
      PrintFormat("ARROW: %s — FALHOU apos %d tentativas (erro %d)",
                  TimeToString(dia_ini, TIME_DATE), InpTentativas, GetLastError());
      return(-1);
   }
   if(got == 0)
      return(0);

   int h = FileOpen(fname, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consegui abrir %s (erro %d)", fname, GetLastError());
      return(-1);
   }
   FileWriteString(h, CSV_HEADER + "\r\n");

   // bid_vol/ask_vol = 0: o broker nao fornece volume por lado. Colunas
   // existem so para compatibilidade de esquema com raw/ (ADR 0005).
   for(int i = 0; i < got; i++)
   {
      long utc_msc = ticks[i].time_msc - (g_offset_sec * 1000);
      FileWriteString(h, StringFormat("%s,%.*f,%.*f,0,0\r\n",
                                      FormatUtcMsc(utc_msc),
                                      g_digits, ticks[i].bid,
                                      g_digits, ticks[i].ask));
   }
   FileClose(h);
   return(got);
}

//+------------------------------------------------------------------+
void OnStart()
{
   if(!SymbolSelect(InpSymbol, true))
   {
      PrintFormat("ARROW: simbolo %s indisponivel.", InpSymbol);
      return;
   }
   g_digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);

   // sonda de escrita: sem a junction Files\ARROW -> data, o dado ficaria na
   // pasta do terminal e o script "funcionaria" em silencio
   string probe = OUT_DIR + "\\_probe.tmp";
   int hp = FileOpen(probe, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hp == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consigo escrever em %s (erro %d). Rode tools/setup/junctions.ps1.",
                  OUT_DIR, GetLastError());
      return;
   }
   FileClose(hp); FileDelete(probe);

   g_offset_sec = MeasureOffsetSec();

   datetime ini = StringToTime(InpDataIni + " 00:00");
   datetime fim = StringToTime(InpDataFim + " 00:00");
   if(ini <= 0 || fim <= ini)
   {
      Print("ARROW: intervalo invalido. Use AAAA.MM.DD.");
      return;
   }

   PrintFormat("ARROW TickBackfill: %s de %s a %s, offset servidor-UTC = %d s",
               InpSymbol, TimeToString(ini, TIME_DATE), TimeToString(fim, TIME_DATE),
               (int)g_offset_sec);
   Print("ARROW: o relogio do servidor e fixo (secao 10.7), entao o offset constante ",
         "vale mesmo atravessando fronteira de DST.");

   long total = 0;
   int  dias_ok = 0, dias_vazios = 0, dias_falha = 0;
   datetime primeiro = 0, ultimo = 0;

   for(datetime d = ini; d < fim; d += 86400)
   {
      if(IsStopped())
      {
         Print("ARROW: interrompido pelo operador.");
         break;
      }
      MqlDateTime dt;
      TimeToStruct(d, dt);
      string fname = StringFormat("%s\\%s-%04d%02d%02d.csv",
                                  OUT_DIR, InpSymbol, dt.year, dt.mon, dt.day);

      int n = PuxarDia(d, fname);
      if(n < 0)      { dias_falha++;  continue; }
      if(n == 0)     { dias_vazios++; continue; }

      dias_ok++;
      total += n;
      if(primeiro == 0) primeiro = d;
      ultimo = d;
      PrintFormat("ARROW: %s — %d ticks", TimeToString(d, TIME_DATE), n);
   }

   Print("ARROW TickBackfill: concluido.");
   PrintFormat("ARROW: %d dias com dado, %d vazios, %d falhas. Total %d ticks.",
               dias_ok, dias_vazios, dias_falha, (int)total);
   if(dias_ok > 0)
      PrintFormat("ARROW: cobertura efetiva de %s a %s",
                  TimeToString(primeiro, TIME_DATE), TimeToString(ultimo, TIME_DATE));
   if(dias_vazios > 0)
      Print("ARROW: dias vazios sao normal em fim de semana. Se um dia UTIL veio vazio, ",
            "e a janela de retencao do broker que ja o descartou.");
   Print("ARROW: saida em data/broker_hist/");
}
//+------------------------------------------------------------------+
