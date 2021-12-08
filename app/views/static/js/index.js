google.charts.load("current", { "packages": ["corechart", "controls"] });

// Config
let config = {
    productCode: "BTC_JPY",
    limit: 100,
    chartSize: 400,
    duration: "1m",
    api: {
        enable: true,
        interval: 3000,
    },
    events: {
        enable: false
    },
    analysis: {
        ema: {
            enable: false,
            period1: 7,
            period2: 14,
            period3: 50,
        },
        bbands: {
            enable: false,
            n: 20,
            k: 2,
        },
        rsi: {
            enable: false,
            period: 14,
            overbought: 70,
            oversold: 30,
        },
        macd: {
            enable: false,
            shortPeriod: 12,
            longPeriod: 26,
            signalPeriod: 9
        }
    }

}

let dataIndicies = {
    numView: 5,
    eventsIndicies: [],
    analysis: {
        emaIndicies: [],
        bbandsIndicies: [],
        rsiIndicies: [],
        macdIndicies: [],
    }
}

// ローソク足のデータ
let candleDataTable;


// DateTimeFormat
function dateTimeFormatByDuration(duration) {
    switch (duration) {
        case '1s': return 'm:ss';
        case '1m': return 'H:mm';
        case '1h': return 'd H';
        case '1d': return 'M d';
    }
}

// durationを変更する
function changeDuration(duration) {
    config.duration = duration;
    send();
}

// チャート図を描画
function drawVisualization(data) {
    // ダッシュボードを作成
    let dashboard = new google.visualization.Dashboard($("#dashboardDiv")[0]);

    // スライダーを作成
    let rangeSlider = new google.visualization.ControlWrapper({
        controlType: "ChartRangeFilter",
        containerId: "filterDiv",
        options: {
            filterColumnLabel: "Date",
            ui: {
                chartType: "LineChart",
                chartOptions: {
                    hAxis: {
                        format: dateTimeFormatByDuration(config.duration),
                    },
                    height: 100
                },
                chartView: {
                    columns: [0, 3] // [Date, Close]
                }
            }
        },

    });

    // 各チャートをまとめて格納する
    // 後にスライダーとまとめてbindするため
    let charts = [];

    // メインチャートを作成
    let mainChart = new google.visualization.ChartWrapper({
        chartType: "ComboChart",
        containerId: "chartDiv",
        options: {
            title: "Chart",
            hAxis: {
                title: "Time",
                format: dateTimeFormatByDuration(config.duration),
            },
            legend: "none",
            height: config.chartSize,
            candlestick: {
                fallingColor: { strokeWidth: 1, fill: 'white' },
                risingColor: { strokeWidth: 1, fill: 'blue' }
            },
            seriesType: "candlesticks",
            series: {},

        },
        view: {
            columns: [0, 1, 2, 3, 4]    // [Date, Low, Open, Close, High]
        }
    });
    charts.push(mainChart);

    // メインチャートのoptionsとviewに各インジケータの情報を追加する
    let mainOptions = mainChart.getOptions();
    let mainView = mainChart.getView();


    // EMA
    if (config.analysis.ema.enable) {
        for (let i = 0; i < dataIndicies.analysis.emaIndicies.length; i++) {
            const index = dataIndicies.analysis.emaIndicies[i];

            mainOptions.series[index] = {
                type: "line",
                lineWidth: 1,
            };
            mainView.columns.push(dataIndicies.numView + index);
        }
    }

    // BBands
    if (config.analysis.bbands.enable) {
        for (let i = 0; i < dataIndicies.analysis.bbandsIndicies.length; i++) {
            const index = dataIndicies.analysis.bbandsIndicies[i];
            mainOptions.series[index] = {
                type: "line",
                color: "#6495ed",
                lineWidth: 1,
            };
            mainView.columns.push(dataIndicies.numView + index);
        }
    }
    
    // Signal events
    if (config.events.enable) {
        const index = dataIndicies.eventsIndicies[0]
        mainOptions.series[index] = {
            type: "line",
            enableInteractivity: false,
            lineWidth: 0
        }
        mainView.columns.push(dataIndicies.numView + index);
        mainView.columns.push(dataIndicies.numView + index + 1);

    }

    // RSI
    if (config.analysis.rsi.enable) {
        let valuesIndex = dataIndicies.numView + dataIndicies.analysis.rsiIndicies[0];
        let overboughtIndex = dataIndicies.numView + dataIndicies.analysis.rsiIndicies[1];
        let oversoldIndex = dataIndicies.numView + dataIndicies.analysis.rsiIndicies[2];
        let rsiChart = new google.visualization.ChartWrapper({
            chartType: "LineChart",
            containerId: "rsiDiv",
            options: {
                title: "RSI",
                hAxis: {
                    format: dateTimeFormatByDuration(config.duration),
                },
                legend: "none",
                colors: ["gray", "gray", "red"]

            },
            view: {
                columns: [0, overboughtIndex, oversoldIndex, valuesIndex]
            }
        });
        charts.push(rsiChart);
        $("#rsi_div").show();
    } else {
        $("#rsi_div").hide();
    }


    // MACD
    if (config.analysis.macd.enable) {
        let macdIndex = dataIndicies.numView + dataIndicies.analysis.macdIndicies[0];
        let signalIndex = dataIndicies.numView + dataIndicies.analysis.macdIndicies[1];
        let histogramIndex = dataIndicies.numView + dataIndicies.analysis.macdIndicies[2];
        let macdChart = new google.visualization.ChartWrapper({
            chartType: "ComboChart",
            containerId: "macdDiv",
            options: {
                title: "MACD",
                hAxis: {
                    format: dateTimeFormatByDuration(config.duration),
                },
                legend: "none",
                seriesType: "line",
                series: {
                    2: { type: "bars" }
                },

            },
            view: {
                columns: [0, macdIndex, signalIndex, histogramIndex]
            }
        })
        charts.push(macdChart);
        $("#macdDiv").show();
    } else {
        $("#macdDiv").hide();
    }




    // ボリュームチャートを作成
    let volumeChart = new google.visualization.ChartWrapper({
        chartType: "ColumnChart",
        containerId: "volumeDiv",
        options: {
            title: "Volume",
            hAxis: {
                format: dateTimeFormatByDuration(config.duration)
            },
            legend: "none",

        },
        view: {
            columns: [0, 5] // [Date, Volume]
        }

    });
    charts.push(volumeChart);

    // エラーメッセージをコンソールログに出す
    logErrorMessage(charts);

    // 各チャートとスライダーをbind
    dashboard.bind(rangeSlider, charts);
    // データをダッシュボードに渡して描画
    dashboard.draw(candleDataTable);
}


function logErrorMessage(charts){
    for(let i=0; i < charts.length; i++){
        google.visualization.events.addListener(charts[i], "error", function(error){
            console.error(error.message);
        })
    }
}

// Ajaxでcandleを取得するAPI通信を行う
// 成功時には結果をcandleDataTableに格納する
function send() {
    if (!config.api.enable){
        return
    }
    
    let params = {
        product_code: config.productCode,
        limit: config.limit,
        duration: config.duration,
    }
    if (config.events.enable) {
        params["events"] = true;
    }
    if (config.analysis.ema.enable) {
        params["ema"] = true;
        params["ema_period1"] = config.analysis.ema.period1;
        params["ema_period2"] = config.analysis.ema.period2;
        params["ema_period3"] = config.analysis.ema.period3;
    }
    if (config.analysis.bbands.enable) {
        params["bbands"] = true;
        params["bbands_n"] = config.analysis.bbands.n;
        params["bbands_k"] = config.analysis.bbands.k;
    }
    if (config.analysis.rsi.enable) {
        params["rsi"] = true;
        params["rsi_period"] = config.analysis.rsi.period;
    }
    if (config.analysis.macd.enable) {
        params["macd"] = true;
        params["macd_short_period"] = config.analysis.macd.shortPeriod;
        params["macd_long_period"] = config.analysis.macd.longPeriod;
        params["macd_signal_period"] = config.analysis.macd.signalPeriod;
    }


    $.ajax({
        url: "/api/candle",
        method: "GET",
        data: params
    })
        .done((result) => {
            candleDataTable = new google.visualization.DataTable();

            // カラムの追加
            candleDataTable.addColumn("date", "Date");
            candleDataTable.addColumn("number", "Low");
            candleDataTable.addColumn("number", "Open");
            candleDataTable.addColumn("number", "Close");
            candleDataTable.addColumn("number", "High");
            candleDataTable.addColumn("number", "Volume");

            let columnIndex = 1;


            // EMA
            let emas = result.emas;
            let emas1 = [];
            let emas2 = [];
            let emas3 = [];
            if (emas != undefined) {
                emas1 = emas[0].values;
                emas2 = emas[1].values;
                emas3 = emas[2].values;
                let period1 = emas[0].period;
                let period2 = emas[1].period;
                let period3 = emas[2].period;
                candleDataTable.addColumn("number", "EMA" + period1.toString());
                candleDataTable.addColumn("number", "EMA" + period2.toString());
                candleDataTable.addColumn("number", "EMA" + period3.toString());
                dataIndicies.analysis.emaIndicies = [columnIndex, columnIndex + 1, columnIndex + 2];
                columnIndex += 3;
            }


            // BBands
            let bbands = result.bbands;
            let bbDown = [];
            let bbMid = [];
            let bbUp = [];
            if (bbands != undefined) {
                bbDown = bbands.down;
                bbMid = bbands.mid;
                bbUp = bbands.up;
                candleDataTable.addColumn("number", "BBands down");
                candleDataTable.addColumn("number", "BBands mid");
                candleDataTable.addColumn("number", "BBands up");
                dataIndicies.analysis.bbandsIndicies = [columnIndex, columnIndex + 1, columnIndex + 2];
                columnIndex += 3;
            }


            // Signal Events
            let events = result.events;
            let eventSignals = []
            $("#signalNotes").html("");
            if (events != undefined) {
                eventSignals = events.signals;
                // マーカーの位置
                candleDataTable.addColumn("number", "Marker");
                // sideを表すannotation
                candleDataTable.addColumn({ type: "string", role: "annotation" });
                dataIndicies.eventsIndicies = [columnIndex, columnIndex+1];
                columnIndex += 2;

                // SignalEventの詳細を表示
                let formatter = new google.visualization.DateFormat({formatType: "medium"});
                for(let i=0; i<eventSignals.length; i++){
                    let event = eventSignals[eventSignals.length - i - 1];
                    const time = formatter.formatValue(new Date(event.time));
                    let text = `<li><div> ${time} . ${event.side} . ${event.price}</div> <div> ${event.notes}</div></li>`;
                    $("#signalNotes").append(text);
                }
                
                // 利益総額を表示
                let profit = events.profit;
                $("#profit").html(profit);
            }

            // RSI
            let rsi = result.rsi;
            let rsiValues = [];
            if (rsi != undefined) {
                rsiValues = rsi.values;
                candleDataTable.addColumn("number", "RSI");
                candleDataTable.addColumn("number", "RSI overbought");
                candleDataTable.addColumn("number", "RSI oversold");
                dataIndicies.analysis.rsiIndicies = [columnIndex, columnIndex + 1, columnIndex + 2];
                columnIndex += 3;
            }


            // MACD
            let macd = result.macd;
            let macdValues = [];
            let macdSignal = [];
            let macdHistogram = [];
            if (macd != undefined) {
                macdValues = macd.macd;
                macdSignal = macd.signal;
                macdHistogram = macd.histogram;
                candleDataTable.addColumn("number", "MACD");
                candleDataTable.addColumn("number", "MACD Signal");
                candleDataTable.addColumn("number", "MACD Histogram");
                dataIndicies.analysis.macdIndicies = [columnIndex, columnIndex + 1, columnIndex + 2];
                columnIndex += 3;
            }


            // データをcandleDataTableに追加
            let candles = result.candles;

            for (let i = 0; i < candles.length; i++) {
                let candle = candles[i];
                let date = new Date(candle.time);
                let row = [date, candle.low, candle.open, candle.close, candle.high, candle.volume];

                // EMA
                if (emas != undefined) {
                    row.push(emas1[i]);
                    row.push(emas2[i]);
                    row.push(emas3[i]);
                }

                // BBands
                if (bbands != undefined) {
                    row.push(bbDown[i]);
                    row.push(bbMid[i]);
                    row.push(bbUp[i]);
                }

                
                // Signal events
                if (events != undefined){
                    let event = eventSignals[0];
                    if (event == undefined){
                        row.push(null);
                        row.push(null);
                    } else if (event.time == candle.time){
                        row.push(candle.high + 1);
                        row.push(event.side);
                        eventSignals.shift();
                    } else {
                        row.push(null);
                        row.push(null);
                    }
                }

                // RSI
                if (rsi != undefined) {
                    row.push(rsiValues[i]);
                    row.push(config.analysis.rsi.overbought);
                    row.push(config.analysis.rsi.oversold);
                }

                // MACD
                if (macd != undefined) {
                    row.push(macdValues[i]);
                    row.push(macdSignal[i]);
                    row.push(macdHistogram[i]);
                }

                candleDataTable.addRows([row]);
            }

            // チャートを描画
            drawVisualization(candleDataTable);
        })
}



// onload
$(window).on('load', function () {
    send();

    // 一定間隔でAPI通信を行い、candleのデータを取得
    let sendTimerId = setInterval(send, config.api.interval);

    // dashboard中にマウスがあるときはデータの更新をしない
    $("#dashboardDiv").on({
        "mouseenter mouseover": function(){
            config.api.enable = false;
        },
        "mouseleave mouseout": function(){
            config.api.enable = true;
        }
    })


    $("#inputApiStop").on("change", function () {
        config.api.enable = !this.checked;
    })

    $("#inputLimit").on("change", function(){
        config.limit = this.value;
        send();
    });

    $("#inputChartSize").on("change", function(){
        config.chartSize = this.value;
        send();
    });

    $("#inputEvents").on("change", function () {
        config.events.enable = this.checked;
        send();
        if (!config.events.enable) {
            $("#profit").html("");
        }
    })

    $("#inputEma").on("change", function () {
        config.analysis.ema.enable = this.checked;
        send();
    });

    $("#inputEmaPeriod1").on("change", function () {
        config.analysis.ema.period1 = this.value;
        send();

    });
    $("#inputEmaPeriod2").on("change", function () {
        config.analysis.ema.period2 = this.value;
        send();

    });
    $("#inputEmaPeriod3").on("change", function () {
        config.analysis.ema.period3 = this.value;
        send();

    });

    $("#inputBBands").on("change", function () {
        config.analysis.bbands.enable = this.checked;
        send();
    });

    $("#inputBBandsN").on("change", function () {
        config.analysis.bbands.n = this.value;
        send();
    });
    $("#inputBBandsK").on("change", function () {
        config.analysis.bbands.k = this.value;
        send();
    });

    $("#inputRSI").on("change", function () {
        config.analysis.rsi.enable = this.checked;
        send();
    });
    $("#inputRSIPeriod").on("change", function () {
        config.analysis.rsi.period = this.value;
        send();
    });

    $("#inputMACD").on("change", function () {
        config.analysis.macd.enable = this.checked;
        send();
    });
    $("#inputMACDShortPeriod").on("change", function () {
        config.analysis.macd.shortPeriod = this.value;
        send();
    });
    $("#inputMACDLongPeriod").on("change", function () {
        config.analysis.macd.longPeriod = this.value;
        send();
    });
    $("#inputMACDSignalPeriod").on("change", function () {
        config.analysis.macd.signalPeriod = this.value;
        send();
    });
})