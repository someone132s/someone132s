initCheckBoxEvent = function (parentTarget, personId, payLoadType, lisId, chartsmonth, chartsyear) {
    parentTarget.find(".check_main").on('click', '.check_goEchart_tr', function (event) {
        event.preventDefault();
        event.stopPropagation();
        $(this).siblings().find('.check_goEchart').removeClass("checked").html("&#xe63e;");
        $(this).find('.check_goEchart').toggleClass("checked");
        if ($(this).find('.check_goEchart').hasClass("checked")) {
            $(this).find('.check_goEchart').html("&#xe740;");
        } else {
            $(this).find('.check_goEchart').removeClass("checked").html("&#xe63e;");
        }
        initLisHistory(parentTarget, personId, payLoadType, lisId, chartsmonth, chartsyear);
    })
}
initLisHistory = function (parentTarget, personId, payLoadType, lisId, chartsmonth, chartsyear) {
    //初始化历史数据echarts
    var myChart = echarts.init(parentTarget.find('.main').get(0));
    var baseData; // 检验勾选数据
    var baseXasixList; // 检验勾选数据 时间节点
    var directionT = "fan";
    var _timecheck = chartsyear;
    var aaa = "";
    var bbb = [];
    // 累计选择数据
    var isgridY = 85;
    parentTarget.find(".check_main").find(".check_goEchart.checked").each(function () {
        aaa = aaa + ($(this).parent().find("span").text()) + "!";
        bbb.push($(this).parent().find("span").text());
    });
    //判断勾选长度，来判断是否实现折线图
    const ischecked = parentTarget.find(".check_main").find(".check_goEchart.checked").length;
    if(ischecked>0){
        parentTarget.find(".rightTable.main").removeClass('hide');
        myChart.resize();
    }else{
        parentTarget.find(".rightTable.main").addClass('hide');
    }

    $.post(navRoot + "/api/getEchartsData", {
        // $.post(Localhost + "document/getLisHistory.do?emrUser=user1&isMenZenFilter=false", {
        personId: personId,
        item: aaa,
        direction: directionT,
        payLoadType: payLoadType
    }, function (data) {

        if (data["code"] == 200 && data["data"] != "false") {

            var resultList = data["data"].list;

            baseData = resultList; // 获取勾选数据
            baseXasixList = data["data"].xasixList.reverse();
            // if (resultList.length == 0) {
            //     $("#main").html("");
            // }

            $.each(resultList, function (i, vo) {
                if (vo.unit == null) {
                    vo.unit = "";
                }
                vo['dateArr'] = vo['dateArr'].reverse();
                vo['docidArr'] = vo['docidArr'].reverse();
                vo['trueValueArr'] = vo['trueValueArr'].reverse();
                vo['valueArr'] = vo['valueArr'].reverse();
                if (i === 0) {
                    var markPoint = {};
                    markPoint.data = [];
                    for (var i = 0; i < vo.valueArr.length; i++) {

                        if (vo.dateArr[i].indexOf(_timecheck) > -1) {
                            if (lisId == vo.docidArr[i]) { // 如果唯一lisid  （LIS）适配，气泡标记本次检验结果
                                var overLis = {
                                    name: vo.dateArr[i],
                                    xAxis: vo.indexArr[i],
                                    yAxis: vo.trueValueArr[i],
                                    value: vo.trueValueArr[i],
                                    symbolSize: 50
                                };
                                markPoint['data'].push(overLis);
                                // } else {
                                //     if (vo.minReference != null && Number(vo.trueValueArr[i]) < vo.minReference) {
                                //         var overMax = {
                                //             name: vo.dateArr[i] + '↓',
                                //             xAxis: vo.indexArr[i],
                                //             yAxis: vo.valueArr[i],
                                //             value: vo.trueValueArr[i],
                                //             symbolSize: 1
                                //         };
                                //         markPoint['data'].push(overMax);
                                //     } else if (vo.maxReference != null && Number(vo.trueValueArr[i]) > vo.maxReference) {
                                //         var overMin = {
                                //             name: vo.dateArr[i] + '↑',
                                //             xAxis: vo.indexArr[i],
                                //             yAxis: vo.valueArr[i],
                                //             value: vo.trueValueArr[i],
                                //             symbolSize: 1
                                //         };
                                //         markPoint['data'].push(overMin);
                                //     }
                            }
                        }
                    }

                    option = {
                        tooltip: {
                            trigger: 'item',
                            confine: true,
                            extraCssText: 'max - width: none; overflow: visible;',
                            formatter: function (params) {
                                if(!params.seriesName && !Array.isArray(params.value)) return;
                                return params.seriesName + '<br/>' +
                                    params.value[4] +
                                    '：' + params.value[3] + ' ' + params.value[5];
                            }
                        },
                        legend: {
                            data: [vo.item], //titlename
                            y: '20px'
                        },

                        // toolbox: {
                        //     show: true,
                        //     x: 'left',
                        //     y: 'bottom',
                        //     feature: {
                        //         myTool_1: {
                        //             show: true,
                        //             title: '时间正序',
                        //             icon: 'image://' + Localhost + 'view/images/zheng.png',
                        //             onclick: function () {
                        //                 directionT = "zheng";
                        //                 initLisHistory(personId, payLoadType, index, lisId);
                        //             }
                        //         },
                        //         myTool_2: {
                        //             show: true,
                        //             title: '时间逆序',
                        //             icon: 'image://' + Localhost + 'view/images/fan.png',
                        //             onclick: function () {
                        //                 directionT = "fan";
                        //                 initLisHistory(personId, payLoadType, index, lisId);
                        //             }
                        //         }
                        //     }
                        // },
                        grid: {
                            x: 20,
                            y: isgridY,
                            x2: 15,
                            y2: 85,
                            left: '11%',
                            bottom: '25%'
                        }
                        ,
                        // calculable: true,
                        xAxis: [{
                            type: 'value',
                            axisLine: {
                                show: false
                            },
                            axisTick: {
                                show: false
                            },
                            axisLabel: {
                                formatter: function (value) {
                                    if (data["data"].xasixList[value] && data["data"].xasixList[value].indexOf(_timecheck) > -1) {
                                        return data["data"].xasixList[value];
                                    }
                                },
                                textStyle: {
                                    fontSize: 12,
                                },
                                rotate: 52,
                            },
                            splitLine: {
                                lineStyle: {
                                    type: 'dashed'
                                }
                            },
                        }],
                        dataZoom:
                            { // echarts 数据过于密集 新增拉伸功能
                                type: 'slider', //图表下方的伸缩条
                                show: true, //是否显示
                                realtime: true, //拖动时，是否实时更新系列的视图
                                start: 0, //伸缩条开始位置（1-100），可以随时更改
                                end: 100, //伸缩条结束位置（1-100），可以随时更改
                                backgroundColor: '#fff',
                                orientL: 'horizontal'
                            }
                        ,
                        yAxis: [{
                            type: 'value',
                            axisLine: {
                                show: false
                            },
                            axisTick: {
                                show: false
                            },
                            min: function (value) {
                                return value.min;
                            },
                            max: function (value) {
                                return value.max;
                            },
                            scale: true,
                            axisLabel: {
                                show: true,
                                rotate: 45 // 旋转45度
                            },
                            splitLine: {
                                lineStyle: {
                                    type: 'dashed'
                                }
                            },
                        }],
                        series:
                            [{
                                name: vo.item,
                                type: 'line',
                                markPoint: markPoint,
                                label: {show: false, textBorderWidth: 0},
                                itemStyle: {
                                    normal: {
                                        lineStyle: {
                                            width: 1 // 折线宽度
                                        }
                                    }
                                },
                                symbolSize: 13,
                                clickable: false,
                                data: (function () {
                                    var d = [];
                                    var e = vo.indexArr;
                                    var f = vo['trueValueArr'];
                                    var g = vo.docidArr;
                                    var h = vo.trueValueArr;
                                    var j = vo.dateArr;
                                    var unit = vo.unit;
                                    var len = 0;
                                    while (len++ < e.length) {
                                        if (j[len - 1].indexOf(_timecheck) > -1) {
                                            d.push([e[len - 1], f[len - 1], g[len - 1], h[len - 1], j[len - 1], unit]);
                                        }
                                    }
                                    return d;
                                })()
                            }]
                    }
                    ;


                } else {

                    // echarts 数据过于密集 新增拉伸功能
                    option.dataZoom = {
                        type: 'slider', //图表下方的伸缩条
                        show: true, //是否显示
                        realtime: true, //拖动时，是否实时更新系列的视图
                        start: 0, //伸缩条开始位置（1-100），可以随时更改
                        end: 100, //伸缩条结束位置（1-100），可以随时更改
                        backgroundColor: '#fff',
                        orientL: 'horizontal'

                    }

                    option.legend.data.push(vo.item);
                    var markPoint = {};
                    markPoint.data = [];
                    for (var i = 0; i < vo.valueArr.length; i++) {

                        if (vo.dateArr[i].indexOf(_timecheck) > -1) {
                            if (lisId == vo.docidArr[i]) { // 如果唯一lisid  （LIS）适配，气泡标记本次检验结果
                                var overLis = {
                                    name: vo.dateArr[i],
                                    xAxis: vo.indexArr[i],
                                    yAxis: vo.trueValueArr[i],
                                    value: vo.trueValueArr[i],
                                    symbolSize: 50
                                };
                                markPoint['data'].push(overLis);
                                // } else {
                                //     if (vo.minReference != null && Number(vo.trueValueArr[i]) < vo.minReference) {
                                //         var overMax = {
                                //             name: vo.dateArr[i] + '↓',
                                //             xAxis: vo.indexArr[i],
                                //             yAxis: vo.valueArr[i],
                                //             value: vo.trueValueArr[i],
                                //             symbolSize: 1
                                //         };
                                //         markPoint['data'].push(overMax);
                                //     } else if (vo.maxReference != null && Number(vo.trueValueArr[i]) > vo.maxReference) {
                                //         var overMin = {
                                //             name: vo.dateArr[i] + '↑',
                                //             xAxis: vo.indexArr[i],
                                //             yAxis: vo.valueArr[i],
                                //             value: vo.trueValueArr[i],
                                //             symbolSize: 1
                                //         };
                                //         markPoint['data'].push(overMin);
                                //     }
                            }
                        }
                    }


                    option.series.push({
                        name: vo.item,
                        type: 'line',
                        markPoint: markPoint,
                        label: {show: false, textBorderWidth: 0},
                        itemStyle: {
                            normal: {
                                lineStyle: {
                                    width: 1 // 折线宽度
                                }
                            }
                        },
                        symbolSize: 10,
                        clickable: false,
                        data: (function () {
                            var d = [];
                            var e = vo.indexArr;
                            var f = vo.trueValueArr;
                            var g = vo.docidArr;
                            var h = vo.trueValueArr;
                            var j = vo.dateArr;
                            var unit = vo.unit;
                            var len = 0;
                            while (len++ < e.length) {
                                if (j[len - 1].indexOf(_timecheck) > -1) {
                                    d.push([e[len - 1], f[len - 1], g[len - 1], h[len - 1], j[len - 1], unit]);
                                }
                            }

                            return d;
                        })()
                    });
                }


            });
            myChart.clear();
            myChart.hideLoading();
            myChart.setOption(option);


        }
    });

};