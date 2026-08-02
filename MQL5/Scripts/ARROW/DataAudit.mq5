//+------------------------------------------------------------------+
//|                                                    DataAudit.mq5 |
//|                                                    ARROW project |
//+------------------------------------------------------------------+
//
// Auditoria do lado do broker. Nao e sensor, e infraestrutura (secao 18 item 6).
//
// Produz:
//   1. Spec do simbolo — digits, point, tick value, contract size, volume,
//      stops level, swap. A tabela da secao 13 e PREMISSA NAO VERIFICADA; isto
//      a confronta com o que o servidor realmente responde.
//   2. Tick value efetivo em JPY, para fechar a conta de sizing na moeda da
//      conta.
//   3. Inventario de historico M1 e de tick real.
//   4. VERIFICACAO DE FUSO pelo metodo da secao 10.7.
//
// O TESTE DE FUSO
//   A manutencao do COMEX e 17:00-18:00 em Nova York. Em UTC isso e
//   21:00-22:00 no horario de verao americano e 22:00-23:00 no inverno --
//   porque Nova York muda, e UTC nao.
//
//   O simbolo tem uma parada diaria observada as 20:58-22:00 em hora de
//   servidor. Logo:
//
//     * Se o relogio do servidor for FIXO em UTC, a parada aparece as 20:58 em
//       julho e DESLIZA para 21:58 em janeiro.
//     * Se o servidor acompanhar o DST americano, a parada fica nas 20:58 nos
//       dois meses.
//
//   O teste e medir a hora da parada em janeiro e em julho e ver se ela se
//   move. Nao depende de fonte externa: o simbolo se testa contra si mesmo.
//
//   POR QUE NAO TimeCurrent() vs TimeGMT(): essas duas funcoes medem o offset
//   NO INSTANTE DA CHAMADA. Entregam uma estacao so, e um servidor que desloca
//   uma hora em marco produz leitura identica a um que nunca desloca. O
//   criterio seria satisfeito por uma medicao incapaz de detectar DST.
//
// SAIDA
//   CSV em data/audit/ pela junction Files\ARROW -> data. O relatorio em
//   markdown e montado pelo lado Python, a partir destes CSVs.
//
#property copyright "ARROW"
#property version   "1.00"
#property script_show_inputs
#property description "Auditoria de spec do simbolo e verificacao de fuso. Nao negocia."

input string InpSymbol      = "XAUUSDm";   // Simbolo a auditar
input string InpSymbolAlt   = "";         // Segundo simbolo (vazio = pular)
//   Vazio por decisao: ADR 0007 restringe o projeto a XAUUSDm ate existir
//   catalogo de sensores validado. Auditar um segundo simbolo convida a
//   comparar, comparar convida a testar, e testar o mesmo sensor em dois
//   instrumentos quase identicos e multiplicacao de testes por outra porta.
input int    InpWinterYear  = 2026;        // Ano da amostra de janeiro
input int    InpSummerYear  = 2025;        // Ano da amostra de julho

#define OUT_DIR  "ARROW\\audit"

//+------------------------------------------------------------------+
//| Escreve uma linha chave=valor no CSV de specs.                   |
//+------------------------------------------------------------------+
void W(const int h, const string sym, const string campo, const string valor,
       const string unidade = "")
{
   FileWriteString(h, StringFormat("%s,%s,%s,%s\r\n", sym, campo, valor, unidade));
}

//+------------------------------------------------------------------+
//| Spec do simbolo, confrontada com a secao 13.                     |
//+------------------------------------------------------------------+
void DumpSpec(const int h, const string sym)
{
   if(!SymbolSelect(sym, true))
   {
      PrintFormat("ARROW: simbolo %s indisponivel — pulando.", sym);
      return;
   }

   int    digits   = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point    = SymbolInfoDouble(sym, SYMBOL_POINT);
   double tickval  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ticksize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double contract = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);

   W(h, sym, "digits",             IntegerToString(digits));
   W(h, sym, "point",              DoubleToString(point, 8));
   W(h, sym, "trade_tick_value",   DoubleToString(tickval, 8),  AccountInfoString(ACCOUNT_CURRENCY));
   W(h, sym, "trade_tick_size",    DoubleToString(ticksize, 8));
   W(h, sym, "trade_contract_size", DoubleToString(contract, 2));
   W(h, sym, "currency_base",      SymbolInfoString(sym, SYMBOL_CURRENCY_BASE));
   W(h, sym, "currency_profit",    SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT));
   W(h, sym, "currency_margin",    SymbolInfoString(sym, SYMBOL_CURRENCY_MARGIN));
   W(h, sym, "volume_min",         DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), 2));
   W(h, sym, "volume_max",         DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX), 2));
   W(h, sym, "volume_step",        DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), 2));
   W(h, sym, "stops_level",        IntegerToString(SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL)), "points");
   W(h, sym, "freeze_level",       IntegerToString(SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL)), "points");
   W(h, sym, "spread_current",     IntegerToString(SymbolInfoInteger(sym, SYMBOL_SPREAD)), "points");
   W(h, sym, "spread_float",       (SymbolInfoInteger(sym, SYMBOL_SPREAD_FLOAT) ? "true" : "false"));
   W(h, sym, "swap_long",          DoubleToString(SymbolInfoDouble(sym, SYMBOL_SWAP_LONG), 4));
   W(h, sym, "swap_short",         DoubleToString(SymbolInfoDouble(sym, SYMBOL_SWAP_SHORT), 4));
   W(h, sym, "swap_mode",          IntegerToString(SymbolInfoInteger(sym, SYMBOL_SWAP_MODE)));
   W(h, sym, "swap_rollover3days", IntegerToString(SymbolInfoInteger(sym, SYMBOL_SWAP_ROLLOVER3DAYS)));
   W(h, sym, "chart_mode",         IntegerToString(SymbolInfoInteger(sym, SYMBOL_CHART_MODE)));

   // Tick value efetivo na moeda da conta, por caminho independente do campo
   // SYMBOL_TRADE_TICK_VALUE. Se os dois divergirem, a divergencia e o achado.
   // Movimento de $1/oz em 1 lote: a secao 13 afirma que vale $100.
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   double lucro_1usd = 0.0;
   if(bid > 0 && OrderCalcProfit(ORDER_TYPE_BUY, sym, 1.0, bid, bid + 1.0, lucro_1usd))
      W(h, sym, "lucro_1lote_move_1usd", DoubleToString(lucro_1usd, 2),
        AccountInfoString(ACCOUNT_CURRENCY));
   else
      W(h, sym, "lucro_1lote_move_1usd", "ERRO:" + IntegerToString(GetLastError()));

   // Inventario de historico.
   datetime m1_first = (datetime)SeriesInfoInteger(sym, PERIOD_M1, SERIES_FIRSTDATE);
   W(h, sym, "m1_primeira_barra", TimeToString(m1_first, TIME_DATE | TIME_MINUTES));
   W(h, sym, "m1_barras",         IntegerToString(Bars(sym, PERIOD_M1)));

   datetime tick_first = (datetime)SeriesInfoInteger(sym, PERIOD_M1, SERIES_TERMINAL_FIRSTDATE);
   W(h, sym, "tick_primeira_data", TimeToString(tick_first, TIME_DATE | TIME_MINUTES));

   PrintFormat("ARROW: spec de %s registrada (digits=%d, contract=%.0f, tick_value=%.4f %s)",
               sym, digits, contract, tickval, AccountInfoString(ACCOUNT_CURRENCY));
}

//+------------------------------------------------------------------+
//| Localiza a parada diaria numa janela e devolve as bordas.        |
//|                                                                  |
//| A parada e o maior buraco intradiario entre barras M1. Devolve a |
//| hora e o minuto do INICIO (ultima barra antes do buraco) e do    |
//| FIM (primeira barra depois), em hora de servidor.                |
//+------------------------------------------------------------------+
int FindDailyBreaks(const string sym, const datetime from, const datetime to,
                    const int h_out, const string rotulo)
{
   MqlRates r[];
   int got = CopyRates(sym, PERIOD_M1, from, to, r);
   if(got <= 0)
   {
      PrintFormat("ARROW: sem historico M1 de %s em %s (erro %d).",
                  sym, rotulo, GetLastError());
      return(0);
   }
   PrintFormat("ARROW: %s — %d barras M1 em %s", sym, got, rotulo);

   int achados = 0;
   for(int i = 1; i < got; i++)
   {
      int gap_min = (int)((r[i].time - r[i - 1].time) / 60);

      // A parada dura ~62 min. Fins de semana sao muito maiores e nao
      // interessam aqui; buracos curtos sao falta de liquidez, nao parada.
      if(gap_min < 30 || gap_min > 180)
         continue;

      MqlDateTime ini, fim;
      TimeToStruct(r[i - 1].time + 60, ini);   // primeiro minuto AUSENTE
      TimeToStruct(r[i].time, fim);            // primeiro minuto de volta

      FileWriteString(h_out, StringFormat("%s,%s,%s,%02d:%02d,%02d:%02d,%d\r\n",
                                          sym, rotulo,
                                          TimeToString(r[i - 1].time, TIME_DATE),
                                          ini.hour, ini.min,
                                          fim.hour, fim.min,
                                          gap_min));
      achados++;
   }

   PrintFormat("ARROW: %s — %d paradas diarias identificadas em %s",
               sym, achados, rotulo);
   return(achados);
}

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
   Print("ARROW DataAudit: iniciando. Nao negocia, nao altera nada.");
   PrintFormat("ARROW: conta em %s, servidor '%s'",
               AccountInfoString(ACCOUNT_CURRENCY), AccountInfoString(ACCOUNT_SERVER));

   // --- specs ---------------------------------------------------------------
   int hs = FileOpen(OUT_DIR + "\\symbol_spec.csv",
                     FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(hs == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consigo escrever em %s (erro %d). "
                  "Rode tools/setup/junctions.ps1.", OUT_DIR, GetLastError());
      return;
   }
   FileWriteString(hs, "symbol,campo,valor,unidade\r\n");

   DumpSpec(hs, InpSymbol);
   if(InpSymbolAlt != "")
      DumpSpec(hs, InpSymbolAlt);

   // Offset instantaneo. Registrado por completude, NAO como teste de fuso —
   // ver o cabecalho deste arquivo sobre por que ele nao serve para isso.
   long off = (long)TimeTradeServer() - (long)TimeGMT();
   W(hs, "-", "offset_instantaneo_servidor_menos_gmt", IntegerToString((int)off), "segundos");
   W(hs, "-", "hora_servidor",  TimeToString(TimeTradeServer(), TIME_DATE | TIME_SECONDS));
   W(hs, "-", "hora_gmt",       TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS));
   FileClose(hs);

   // --- fuso: paradas diarias em duas estacoes ------------------------------
   int hb = FileOpen(OUT_DIR + "\\daily_breaks.csv",
                     FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(hb == INVALID_HANDLE)
   {
      PrintFormat("ARROW: nao consigo escrever daily_breaks.csv (erro %d)", GetLastError());
      return;
   }
   FileWriteString(hb, "symbol,estacao,dia,parada_inicio,parada_fim,duracao_min\r\n");

   // Janeiro: inverno americano, COMEX 22:00-23:00 UTC.
   // Julho: verao americano, COMEX 21:00-22:00 UTC.
   // Se o servidor for UTC fixo, a parada desliza uma hora entre os dois.
   datetime jan_ini = StringToTime(StringFormat("%d.01.05 00:00", InpWinterYear));
   datetime jan_fim = StringToTime(StringFormat("%d.01.31 23:59", InpWinterYear));
   datetime jul_ini = StringToTime(StringFormat("%d.07.05 00:00", InpSummerYear));
   datetime jul_fim = StringToTime(StringFormat("%d.07.31 23:59", InpSummerYear));

   int n_jan = FindDailyBreaks(InpSymbol, jan_ini, jan_fim, hb, "inverno_janeiro");
   int n_jul = FindDailyBreaks(InpSymbol, jul_ini, jul_fim, hb, "verao_julho");

   FileClose(hb);

   Print("ARROW DataAudit: concluido.");
   PrintFormat("ARROW: paradas encontradas — janeiro/%d: %d, julho/%d: %d",
               InpWinterYear, n_jan, InpSummerYear, n_jul);

   if(n_jan == 0 || n_jul == 0)
      Print("ARROW: ATENCAO — faltou historico M1 numa das estacoes. ",
            "O teste de fuso EXIGE as duas; com uma so ele nao responde nada. ",
            "Baixe mais historico M1 (abrir grafico M1 e rolar para tras) e rode de novo.");
   else
      Print("ARROW: as duas estacoes tem amostra. ",
            "Se a hora da parada for IGUAL nas duas, o servidor acompanha o DST americano. ",
            "Se DESLIZAR uma hora, o relogio do servidor e fixo.");

   Print("ARROW: saida em data/audit/symbol_spec.csv e data/audit/daily_breaks.csv");
}
//+------------------------------------------------------------------+
