/**
 * Created by lizige on 2019/1/25.
 */
var Module = {};
Module.report = {};
var PayLoadType = {};
$(function () {
    /*
     检查报告标签报告状态

     labelText 标签内容
     valueList 标签取值
     extraClass 增加class(done 绿色  warning 红色)
     */
    var CustomReportStatus = [
        {
            labelText: '报告已出',
            valueList: [10, 11, null, ''],
            extraClass: 'done'
        },
        {
            labelText: '未检查',
            valueList: [0, 1, 2, 3, 4, 5]
        },
        {
            labelText: '已取消',
            valueList: [1000, 1100]
        },
        {
            labelText: '报告未出',
            valueList: [6, 7, 8, 9, 3000],
            extraClass: 'warning'
        }
    ];

    for (var i = 0, il = CustomReportStatus.length; i < il; i++) {
        var _status = CustomReportStatus[i];
        var _class = _status.extraClass ? ' ' + _status.extraClass : '';
        var _html = '<span class="item_title_status' + _class + '">' + _status.labelText + '</span>';
        var children = _status.valueList;

        if (_status.extraFunc) Const.noCheck = _status.labelText;

        for (var j = 0, jl = children.length; j < jl; j++) {
            Const.reportStatus[children[j]] = {};
            Const.reportStatus[children[j]].html = _html;
            Const.reportStatus[children[j]].text = _status.labelText;
        }

    }
    Module.getValue = function (data, orgin) {
        if (data) {
            return data;
        } else {
            return orgin || "";
        }
    }

    Module.report.KT_RECIPE = function (data, json) {
        if (!data || !data[0]) return '';

        var _medNum = 0;
        var _content = '';
        var l = data.length;

        for (var i = 0; i < l; i++) {
            var drugFlag = Module.getValue(data[i].drugFlag);

            _content += '<tr>' +
                '<td>' +
                Module.getValue(data[i].itemName) +
                (Module.getValue(data[i].medname) && '[' + Module.getValue(data[i].medname) + ']') +
                '</td>' +
                '<td>' +
                (drugFlag != '1' ? Module.getValue(data[i].xmmc) : Module.getValue(data[i].specs)) +
                '</td>' +
                '<td>' + Module.getValue(data[i].qty) + '</td>' +
                '<td>' + Module.getValue(data[i].priceUnit) + '</td>' +
                '<td>' + Module.getValue(data[i].doseOnce) + Module.getValue(data[i].doseUnit) + '</td>' +
                '<td>' + Module.getValue(data[i].frequencyCode) + '</td>' +
                '<td>' + Module.getValue(data[i].useName) + '</td>' +
                '</tr>';

            if (drugFlag == '1') {
                _medNum++;
            }
        }

        if (l) {
            _content = '<table class="tableInfo tableNowrap">' +
                '<thead>' +
                '<tr>' +
                '<th>名称</th>' +
                '<th>规格</th>' +
                '<th>数量</th>' +
                '<th>单位</th>' +
                '<th>每次用量</th>' +
                '<th>频次</th>' +
                '<th>用法</th>' +
                '</tr>' +
                '</thead>' +
                '<tbody>' + _content + '</tbody>' +
                '</table>' +
                '<div class="sheet_ul_bottom child_align equal_part_two MT20">' +
                '<em>医师：' + Module.getValue(json.doctName) + '</em>' +
                '<em>审核：</em>' +
                '</div>';
        }

        var _html = '<div class="tableWrapper">' +
            '<div class="content_block">' +
            '<span class="mr50">缴费单号：</span>' +
            '<span>处方号：' + Module.getValue(data[0].cfh) + '</span>' +
            '</div>' +
            '<div class="content_block">地址或电话：</div>' +
            '<div class="content_block">主要诊断：' + Module.getValue(json.mainZD) + '</div>' +
            '<div class="content_block">次要诊断：' + Module.getValue(json.secondaryZD) + '</div>' +
            '<div class="content_block clearfix_for_l">' +
            '<span>开方科室：' + Module.getValue(data[0].kfksname) + '</span>' +
            '<span class="fr">药品：' + _medNum + '</span>' +
            '</div>' +
            '<div class="content_block">' + _content + '</div>' +
            '</div>';

        return _html;
    };

    Module.report.BloodApply = function (data) {
        if (!data) return;

        // var datas = Module.getValue(data.nameValueMap["//body"]?.childList || []);
        var datas = Module.getValue(data.nameValueMap["//body"] ? data.nameValueMap["//body"].childList : []);
        var _html = '';

        for (var i = 0, l = datas.length; i < l; i++) {
            var children = Module.getValue(datas[i].childList);
            var cl = children.length;

            if (cl > 1) {
                var _title = '';
                var _content = '';
                var _bottom = '';

                for (var j = 0; j < cl; j++) {
                    var grandchildren = Module.getValue(children[j].childList);
                    var grandchild = children[j].valueMap;
                    var cdl = grandchildren.length;
                    var _name = Module.removeSpace(Module.getValue(grandchild.name)).replace(/:/g, '').replace(/：/g, '');
                    var _text = Module.getValue(grandchild.text);

                    if (_name == '标题') {

                        _title = '<p class="tableTitle">' + Module.removeSpace(_text) + '</p>';

                    } else if (_name == '主治医师' || _name == '副高及以上' || _name == '专科主任') {

                        _bottom += '<em><label>' + _name + '：</label><span>' + _text + '</span></em>';

                    } else if (_name == '输血科会诊意见' || _name == '医务科审核意见') {

                        _bottom += '<em class="full"><label class="content_tit">' + _name + '：</label><span class="content_text">' + _text + '</span></em>';

                    } else if (_name == "编号") {

                        _content += '<li>' + _text + '</li>';

                    } else if (_name === "") {

                        _content += '<li>' + _text.replace("109/L", "*10^9/L") + '</li>';

                    } else if (cdl) {

                        _content += '<li class="full">' + _name + '：</li>';

                        for (var k = 0; k < cdl; k++) {
                            var _ggrandchild = grandchildren[k].valueMap;
                            _name = Module.removeSpace(Module.getValue(_ggrandchild.name)).replace(/:/g, '').replace(/：/g, '');
                            _text = Module.getValue(_ggrandchild.text);

                            _content += '<li>' + _name + '：' + _text + Module.getValue(Const.bloodApplyUnit[_name]) + '</li>';

                        }

                    } else {

                        _content += '<li>' + _name + '：' + _text + Module.getValue(Const.bloodApplyUnit[_name]) + '</li>';

                    }

                }

                _html += '<div class="tableWrapper">' +
                    _title +
                    '<ul class="sheet_ul clearfix_for_l">' + _content + '</ul>' +
                    '<div class="sheet_ul_bottom clearfix_for_l child_align equal_part_three">' + _bottom + '</div>' +
                    '</div>';
            }
        }

        return _html;
    };
    Module.report.QF_RECIPE = function (data, json) {
        if (!data || !data[0]) return '';

        var _medNum = Module.getValue(data[0].drugNum, 0);
        var _content = '';
        var l = data.length;

        for (var i = 0; i < l; i++) {
            var drugFlag = Module.getValue(data[i].drugFlag);

            _content += '<tr>' +
                '<td>' +
                Module.getValue(data[i].itemName) +
                (Module.getValue(data[i].medname) && '[' + Module.getValue(data[i].medname) + ']') +
                '</td>' +
                '<td>' +
                (drugFlag != '1' ? Module.getValue(data[i].xmmc) : Module.getValue(data[i].specs)) +
                '</td>' +
                '<td>' + Module.getValue(data[i].qty) + '</td>' +
                '<td>' + Module.getValue(data[i].priceUnit) + '</td>' +
                '<td>' + Module.getValue(data[i].doseOnce) + Module.getValue(data[i].doseUnit) + '</td>' +
                '<td>' + Module.getValue(data[i].frequencyCode) + '</td>' +
                '<td>' + Module.getValue(data[i].useName) + '</td>' +
                '</tr>';

        }

        if (l) {
            _content = '<table class="tableInfo tableNowrap">' +
                '<thead>' +
                '<tr>' +
                '<th>名称</th>' +
                '<th>规格</th>' +
                '<th>数量</th>' +
                '<th>单位</th>' +
                '<th>每次用量</th>' +
                '<th>频次</th>' +
                '<th>用法</th>' +
                '</tr>' +
                '</thead>' +
                '<tbody>' + _content + '</tbody>' +
                '</table>' +
                '<div class="sheet_ul_bottom child_align equal_part_two MT20">' +
                '<em>医师：' + Module.getValue(data[0].kfys) + '</em>' +
                '<em>审核：' + Module.getValue(data[0].kfys) + '</em>' +
                '</div>';
        }

        var _html = '<div class="tableWrapper">' +
            '<div class="content_block">' +
            //						'<span class="mr50">缴费单号：</span>' +
            '<span>处方号：' + Module.getValue(data[0].cfh) + '</span>' +
            '</div>' +
            //					'<div class="content_block">地址或电话：</div>' +
            '<div class="content_block">门诊诊断：' + Module.getValue(data[0].mzzd) + '</div>' +
            '<div class="content_block clearfix_for_l">' +
            '<span>开方科室：' + Module.getValue(data[0].kfks) + '</span>' +
            '<span class="fr">药品：' + _medNum + '</span>' +
            '</div>' +
            '<div class="content_block">' + _content + '</div>' +
            '</div>';

        return _html;
    };

    Module.report.RECIPE = function (data, json) {
        if (!data || !data[0]) return '';

        var _medNum = 0;
        var _content = '';
        var l = data.length;

        for (var i = 0; i < l; i++) {
            var drugFlag = Module.getValue(data[i].drugFlag);

            _content += '<tr>' +
                '<td>' +
                Module.getValue(data[i].itemName) +
                (Module.getValue(data[i].medname) && '[' + Module.getValue(data[i].medname) + ']') +
                '</td>' +
                '<td>' +
                (drugFlag != '1' ? Module.getValue(data[i].xmmc) : Module.getValue(data[i].specs)) +
                '</td>' +
                '<td>' + Module.getValue(data[i].qty) + '</td>' +
                '<td>' + Module.getValue(data[i].priceUnit) + '</td>' +
                '<td>' + Module.getValue(data[i].doseOnce) + Module.getValue(data[i].doseUnit) + '</td>' +
                '<td>' + Module.getValue(data[i].frequencyCode) + '</td>' +
                '<td>' + Module.getValue(data[i].useName) + '</td>' +
                '</tr>';

            if (drugFlag == '1') {
                _medNum++;
            }
        }

        if (l) {
            _content = '<table class="tableInfo tableNowrap">' +
                '<thead>' +
                '<tr>' +
                '<th>名称</th>' +
                '<th>规格</th>' +
                '<th>数量</th>' +
                '<th>单位</th>' +
                '<th>每次用量</th>' +
                '<th>频次</th>' +
                '<th>用法</th>' +
                '</tr>' +
                '</thead>' +
                '<tbody>' + _content + '</tbody>' +
                '</table>' +
                '<div class="sheet_ul_bottom child_align equal_part_two MT20">' +
                '<em>医师：' + Module.getValue(data[0].kfys) + '</em>' +
                '<em>审核：' + Module.getValue(data[0].kfys) + '</em>' +
                '</div>';
        }

        var _html = '<div class="tableWrapper">' +
            '<div class="content_block">' +
            '<span class="mr50">缴费单号：</span>' +
            '<span>处方号：' + Module.getValue(data[0].cfh) + '</span>' +
            '</div>' +
            '<div class="content_block">地址或电话：</div>' +
            '<div class="content_block">主要诊断：' + Module.getValue(json.mainZD) + '</div>' +
            '<div class="content_block">次要诊断：' + Module.getValue(json.secondaryZD) + '</div>' +
            '<div class="content_block clearfix_for_l">' +
            '<span>开方科室：' + Module.getValue(data[0].kfksname) + '</span>' +
            '<span class="fr">药品：' + _medNum + '</span>' +
            '</div>' +
            '<div class="content_block">' + _content + '</div>' +
            '</div>';

        return _html;
    };

    Module.report.everyday = function (data) {
        if (!data) return;

        var datas = Module.getValue(data.nameValueMap);
        // var _html = '<div class="tableWrapper">';

        var _html = Module.normalContentMain(datas.contentList);

        // _html += '</div>';

        return _html;
    };
    Module.report.everyday1 = function (data, plt, documentUniqueId) {

        var datas = Module.getValue(data.nameValueMap);

        var _html = '';

        var mainZD = "";
        var secondaryZD = "";
        var visitFlowId = "";
        var doctName = "";

        for (var key in datas) {
            var child = Module.getValue(datas[key].childNodeValueMap);
            var _flag = Module.getValue(child.mainFlag);
            visitFlowId = Module.getValue(child.inpatientNo);
            doctName = Module.getValue(child.doctName);

            if (_flag == '1') {

                mainZD += Module.getValue(child.diagName) + '，';

            } else if (_flag == '0') {

                secondaryZD += Module.getValue(child.diagName) + '，';

            } else {
                continue;
            }
        }

        var jsonForMod = {
            doctName: doctName,
            mainZD: mainZD.substring(0, mainZD.length - 1),
            secondaryZD: secondaryZD.substring(0, secondaryZD.length - 1),
            datas: datas
        };

        var postData = {
            documentUniqueId: documentUniqueId
        };

        $.ajaxSetup({
            async: false
        });

        $.post(navRoot + "/api/inpatient/showinfo/chufang", postData, function (data) {
            // Module.errorJump(json);
            if (data["code"] == 200) {
                _html = Module.report[plt](data["data"], jsonForMod);
            }
        }, "json");

        $.ajaxSetup({
            async: true
        });

        return _html;

    }
// 检查 dom
    Module.report.jianCha = function (data, payLoadType, reportFlag, reportStatus, reason) {
        var _data = {
            "title": Module.getValue(data.title),
            "bgrq": Module.getValue(data.bgrq),
            "bglr": Module.getValue(data.bglr),
            "bgys": Module.getValue(data.bgys),
            "imageFlag": Module.getValue(data.imageFlag),
            "flowFlag": Module.getValue(data.flowFlag),
            "jcsj": Module.getValue(data.jcsj),
            "shys": Module.getValue(data.shys),
            "shsj": Module.getValue(data.shsj),
            "yxzd": Module.getValue(data.yxzd),
            "zdys": Module.getValue(data.zdys),
            "scsj": Module.getValue(data.scsj),
            "bgsj": Module.getValue(data.bgsj),
            "payLoadType": payLoadType,
            "reportStatus": Module.getValue(data.reportStatus),
            "imageBase64IndexList": Module.getValue(data.imageBase64IndexList),
            "xmlPath": Module.getValue(data.xmlPath),
            "imageFlagDescribes": Module.getValue(data.imageFlagDescribes),
            valueMap: Module.getValue(data.valueMap)
        };

        var _tipHtml = '';

        // 外院无影像报告
        if (_data.title && Switch.outsideHospitalTipDisplay) {
            _tipHtml = '外院（' + _data.title + '）报告暂无影像可以调阅';
        }

        var _statusHtml = '';
        var _reportText = Const.reportStatus[reportStatus].text;
        if (_reportText == '报告未出') {
            if (_data.imageFlag == "true") {
                _statusHtml = '该检查医学影像科尚未出具报告，影像仅供参考，不作为临床诊断、治疗的依据。';
            } else {
                _statusHtml = '该病人已检查，影像科尚未出具报告，影像尚未上传完毕。';
            }
        } else if (_reportText == '未检查') {
            _statusHtml = '病人尚未检查，暂无报告。';
        } else if (_reportText == '已取消') {
            _statusHtml = '病人检查取消，无报告。';
        } else {
            _statusHtml = '';
        }

        if (_statusHtml) {
            _tipHtml = _tipHtml ?
                ('1.' + _tipHtml + '2.' + _statusHtml) :
                _statusHtml;
        }

        _tipHtml = _tipHtml && '<div class="tipper tipper_border">' + _tipHtml + '</div>';

        //报告延期
        if (_reportText == '报告延期') {
            _tipHtml = '延期原因：' + reason;
        }
        var images = _data.imageBase64IndexList;
        var _imageHtml = '<div class="all_picpdf"><div class="init_pdf">';

        if (images.length) {
            _imageHtml += '<div class="pic_pdf_logos" style="position:relative;"><p class="js_show_logo show_logos">图片</p>'
            _imageHtml += '<ul class="report_description clearfix js_pdf_logo logos_nav">';

            for (var i = 0, l = images.length; i < l; i++) {
                var src = Const.baseUrl + 'document/generatePicDoc.do?emrUser=8649&xmlPath=' + _data.xmlPath + '&index=' + images[i].index + '&payLoadType=' + _data.payLoadType;

                // 需要确认下效果
                var _title = '<p class="scan_report_image_title">' + Module.getValue(_data.imageFlagDescribes[i]) + '</p>';
                var _liClass = '';
                if (Module.getValue(_data.imageFlagDescribes[i])) {
                    _liClass = 'hasTitle_S';
                }

                var _attr = '';

                if (images[i].width >= images[i].height) {
                    _attr = 'width="100%"';
                } else {
                    _attr = 'height="100%"';
                }

                _imageHtml += '<li class="scan_report_image ' + _liClass + '">' +
                    '<div class="scanImgBox"><img src="' + src + '" ' + _attr + ' /><span>&nbsp;</span></div>' + _title + '</li>';
            }

            _imageHtml += '</ul></div>';
        }
        _imageHtml += '</div><div class="pic_pdf_cent js_pdf_main"></div></div>'

        //  2018-11-29 mmm  oldcode  整体展示报告信息
        var __tabBox = '<div class="report_main scan_report" name="report">' +
            _tipHtml +
            Module.normalContentMain(_data.valueMap.contentList);


        __tabBox += Module.normalContentBottom(_data.valueMap.tableBottomList);
        __tabBox += _imageHtml;
        __tabBox += '</div>';

        //// 报告不存在则隐藏
        //if (reportFlag === false && (_data.imageFlag === 'true' || (_data.flowFlag === 'true'))) {
        //    __tab = '';
        //    __tabBox = '';
        //}

        // 影像部分
        if (_data.imageFlag === 'true') {
        }

        //// 流程图部分
        //if (_data.flowFlag === 'true' && Switch.flowChartDisplay) {
        //    __tab += '<li class="report_menu_tab scan_menu_flow" name="flow">流程</li>';
        //    __tabBox += '<div class="report_main scan_flow" name="flow" style="display: none;"></div>';
        //}

        // 统一表现形式：流程图若唯一TAB依然存在
        var _html = __tabBox;


        return _html;

    };

// 检验 dom
    Module.report.jianYan = function (data, reportFlag, payLoadType, empi) {
        var _data = {
            "bacTestList": Module.getValue(data.bacTestList),
            "instXmlBeans": Module.getValue(data.instXmlBeans),
            "lisBbly": Module.getValue(data.lisBbly),
            "flowFlag": Module.getValue(data.flowFlag),
            "bacteriaBbly": Module.getValue(data.bacteriaBbly),
            "xBacteriaInspectionBeans": Module.getValue(data.xBacteriaInspectionBeans),
            "xBacteriaInspectionTwoBeans": Module.getValue(data.xBacteriaInspectionTwoBeans),
            "bacteriaReportType": Module.getValue(data.bacteriaReportType),
            "reportDoctor": Module.getValue(data.reportDoctor),
            "checkDoctor": Module.getValue(data.checkDoctor),
            "reportTime": Module.getValue(data.reportTime),
            "valueMap": Module.getValue(data.valueMap)
        };
        var _empi = empi; //  2018-11-28 mmm  追加病人empi
        var _html = '';
        var __tab = '<li class="report_menu_tab scan_menu_report active" name="report">报告</li>';
        var __tabBox = '';
        var _flow_tab = '<li class="report_menu_tab scan_menu_flow" name="flow">流程</li>';
        var _flow_wrap = '<div class="report_main scan_flow" name="flow" style="display: none;"></div>';

        var topContent = Module.normalContentMain(_data.valueMap.contentList);
        //  2018-11-29 mmm  检验  标本来源 过滤空数据
        // for (var _len = 0; _len < topContent.length; _len++) {
        // 	if (topContent[_len] == "") {
        // 		topContent.length--;
        // 	}
        // }

        // 获取pdf dom mmm  检验
        // var _pdfHtml2 = $(".js_pdf").html();
        // 常金
        var _pdfHtml2 = '';
        if ($('.each_jianyan_bottom .p_main_each_item.active').find('.item_report_view').length > 0) {
            var _pdfHtml = $(".js_pdf").html();
            _pdfHtml2 = '<div class="js_pdf pdfBox">' + _pdfHtml + '</div>';
        } else {
            _pdfHtml2 = '';
        }
        if (payLoadType == "BacteriaLISBG") {
            __tabBox = Module.BacteriaLISBG(data);
            __tabBox = '<div class="report_main scan_report" name="report">'
                + '<div class="report">' + __tabBox + '</div>'
                + _pdfHtml2 + '</div>';
        } else {

            // 检验dom增加 echarts
            __tabBox = '<div class="report_main scan_report" name="report">' +
                (topContent && ('<div class="check_title">' + topContent + '</div>')) +
                '<div class="check_main">' +
                Module.normalTable(_data.valueMap, false, _empi, payLoadType, 'result', 'item') +
                Module.normalContentBottom(_data.valueMap.tableBottomList) +
                // '<div class="popUp_content" >' + '<ul class="leftMenu fl" id="detailItem_1">' + // 插入ul数据
                // Module.normalUl(_data.valueMap, Const.echartsLinkDisplay, _empi, payLoadType, 'result', 'item') +
                // '</ul>' +
                '<div class="rightTable main hide" style="-webkit-tap-highlight-color: transparent; -webkit-user-select: none;"></div>' +
                // '<div class="rightTable" id="main_doc" style="display: none"></div>' +
                '</div></div>' +
                _pdfHtml2 +
                '</div>';
        }
        _html = __tabBox;

        return _html;

    };

// 通用内容
    Module.normalContentMain = function (data) {
        if (!data) return '';

        var l = data.length;
        var _html = '';
        var _html_other = ''; // 报告文档分开展示 中间插入图片
        var _htmlBlock = [];
        var _htmlTitle = '';
        var _paternity = {};

        var condition = (data[0] && data[0].other == 'title') || (data[1] && data[1].other == 'title' && data[0].other == 'time');

        var _bcbt = '';
        var _bcbg = '';
        var _sliceStart = null;

        for (var i = 0; i < l; i++) {

            var __other = data[i].other;
            var __nextOther = data[i + 1] && data[i + 1].other;

            if (__other == 'time') continue;
            if (__other == 'bcbt') {
                _bcbt = data[i].text;
                continue;
            }
            if (__other == 'title') {

                if (condition) {

                    wrapTitleAndContent();
                    setTitle(i);

                } else {

                    setTitle(i);
                    wrapTitleAndContent();

                }


            } else {

                var _name = Module.removeSpace(Module.getValue(data[i].name)).replace(/:/g, '').replace(/：/g, '');
                var _text = Module.getValue(data[i].text, '无');
                var _index = data[i].index || _htmlBlock.length;
                var _special = data[i].listShow;

                if (__other == 'bcbg') {
                    _name = _bcbt;

                    if (__nextOther == 'bcbz' || __nextOther == 'bcbz,date') {
                        _sliceStart = i;
                        _bcbg = data[i].text;
                        continue;
                    }
                }

                if (__other == 'bcbz' || __other == 'bcbz,date') {

                    if (__nextOther != 'bcbz' && __nextOther != 'bcbz,date') {
                        _name = _bcbt;
                        _text = _bcbg + Module.normalContentBottom(data.slice(_sliceStart + 1, i + 1));
                        _bcbg = '';
                        _index = data[_sliceStart].index || _htmlBlock.length;
                    } else {
                        continue;
                    }
                }

                if (!_name && _text == '无') continue;

                _text = _text.replace(/<image>/g, '<img class="imgTextAlign" src="data:image/jpg;base64,');
                _text = _text.replace(/<\/image>/g, '" />');

                if (_special) {

                    if (!_paternity[_special]) _paternity[_special] = {};

                    if (_special == 'Parent') {
                        _special = data[i].nodeName;

                        _paternity[_special].index = _index;
                        _paternity[_special].name = Module.normalLabelFormat(_name);
                        _htmlBlock[_index] = '';

                    } else {
                        if (!_paternity[_special].text) _paternity[_special].text = '';
                        _paternity[_special].text += _text + ' ';
                    }

                    continue;
                }

                // 此处后台那边修改的 2018-09-20 Chang-Jin
                var _content_text_Html = '';
                if (_text.indexOf("http:") != -1 || _text.indexOf("ftp:") != -1) {
                    _content_text_Html = '<a href="' + _text + '" target="_blank">' + '影像链接' + '</a>';
                } else {
                    _content_text_Html = '<span class="content_text">' + _text + '</span>';
                }


                var _blockHtml = '<div class="report_description clearfix">' +
                    (_name && '<label class="content_tit">【' + Module.normalLabelFormat(_name) + '】</label>') +
                    _content_text_Html +
                    '</div>';

                if (_htmlBlock[_index]) {
                    _htmlBlock.splice(_htmlBlock.length, 0, _htmlBlock[_index]);
                }

                _htmlBlock[_index] = _blockHtml;

            }

        }

        if (_htmlBlock.length) {

            dealPaternity();
            //  2018-11-29 mmm  oldcode  报告详情文档
            _html += '<div class="reportPart">' + (condition ? _htmlTitle : '') + _htmlBlock.join('') + '</div>';
            // _html += '<div class="reportPart">' + (condition ? _htmlTitle : '') + _htmlBlock[0] + '</div>';

            var _htmlBlock_2 = _htmlBlock;
            _htmlBlock_2[0] = '';
            if (_htmlBlock.length > 1) {
                _html_other = '<div class="reportPart">' + (condition ? _htmlTitle : '') + _htmlBlock_2.join('') + '</div>';
            }


        }

        function dealPaternity() {
            for (var key in _paternity) {
                if (key == 'Parent') continue;

                var theNode = _paternity[key];

                if (_htmlBlock[theNode.index]) {
                    _htmlBlock.splice(_htmlBlock.length, 0, _htmlBlock[theNode.index]);
                }

                _htmlBlock[theNode.index] = '<div class="report_description clearfix">' +
                    (theNode.name && '<label class="content_tit">【' +
                        Module.normalLabelFormat(theNode.name) +
                        '】</label>') +
                    '<span class="content_text">' + theNode.text + '</span>' +
                    '</div>';
            }

            _paternity = {};
        }

        function wrapTitleAndContent() {
            if (_htmlBlock.length) {
                dealPaternity();


                //  2018-11-29 mmm  oldcode  报告详情文档
                _html += '<div class="reportPart">' + (condition ? _htmlTitle : '') + _htmlBlock.join('') + '</div>';
                // _html += '<div class="reportPart">' + (condition ? _htmlTitle : '') + _htmlBlock[0].join('') + '</div>';

                var _htmlBlock_2 = _htmlBlock;
                _htmlBlock_2[0] = '';

                if (_htmlBlock.length > 1) {
                    _html_other = '<div class="reportPart">' + (condition ? _htmlTitle : '') + _htmlBlock_2.join('') + '</div>';
                }


                _htmlBlock = [];
            }
        }

        function setTitle(num) {
            var _tit = Module.removeSpace(Module.getValue(data[num].text)).replace(/:/g, '').replace(/：/g, '');

            if (num > 0 && data[num - 1].other == 'time') {

                _htmlTitle = '<div class="recordTitle">' +
                    '<div class="text-common">【' + data[num - 1].text + '】</div>' +
                    '<em>' + _tit + '</em>' +
                    '</div>';

            } else {

                _htmlTitle = '<p class="tableTitle">' + _tit + '</p>';

            }
        }

        return _html;  // oldcode 报告信息集体展示
        /* var all_reporthtml = [_html,_html_other];

         return all_reporthtml; */
    };

// 通用脚注
    Module.normalContentBottom = function (data) {
        if (!data) return '';

        var l = data.length;

        var _html = '';
        var _htmlArr = [];

        for (var i = 0; i < l; i++) {

            var _text = data[i].text;
            if (data[i]["nodeName"] == "shsj") {
                _text = common.dateFormart(_text, "yyyy-MM-dd");
            }
            var _index = data[i].index || _htmlArr.length;

            if (_htmlArr[_index]) {
                _htmlArr.splice(_htmlArr.length, 0, _htmlArr[_index]);
            }
            _htmlArr[_index] = '<em><label>' + data[i].name + '：</label><span>' + _text + '</span></em>';
        }

        if (_htmlArr.length) {
            _html = '<div class="weui-flex text-disabled font12 onlyBottomBorder">' +
                _htmlArr.join('') +
                '</div>';

        }

        return _html;
    };

    // 通用表格
    Module.normalTable = function (data, withEcharts, empi, payLoadType, resultName, paramName) {
        if (!data) return '';
        var _stack;
        var _html = '<table class="table">';
        var _dataThead = Module.getValue(data.tableTitleList);
        var _dataTbody = Module.getValue(data.tableRowList);

        var thL = _dataThead.length;
        var trL = _dataTbody.length;
        var thHtmlArr = [];
        var tdHtmlArr = [];

        for (var i = 0; i < thL; i++) {

            var _th = '<th>' + _dataThead[i].name + '</th>';

            thHtmlArr[_dataThead[i].index] = _th;

        }

        //  2018-11-28 mmm  不需要echarts图标th
        if (withEcharts) {
            thHtmlArr.push('<th width="50"></th>');
        }

        if (thL) _html += '<thead><tr>' + thHtmlArr.join('') + '</thead></tr>';

        _html += '<tbody>';
        
        // 遍历 tr
        for (var k = 0; k < trL; k++) {
            //// echarts小图标移动
            // var _checkinp = '<input class="check_goEchart" type="checkbox"/>';
            // if (k == 0) {
            //     _checkinp = '<input class="check_goEchart" type="checkbox" checked/>';
            // }
            var _checkinp = '<i class="iconfont check_goEchart">&#xe63e;</i>';
            if (_dataTbody[k][1]['text'] == '阴性(―)') {
                _checkinp = '';
            }
            _dataTbody[k][0].text = _checkinp + '<span class="check_goEchart_span">' + _dataTbody[k][0].text + '</span>';

            var tds = _dataTbody[k];
            tdHtmlArr = [];
            if(_dataTbody[k][1]['text'] == "阴性(―)"){
                _html += '<tr>';
            }else{
                _html += '<tr class="check_goEchart_tr">';
            }


            _stack = {};


            // 遍历 th
            for (var j = 0, tdL = thHtmlArr.length; j < tdL; j++) {

                var _td = '<td></td>';
                // var _tdLast = tdL - 1;

                //  2018-11-28 mmm  不需要echarts图标td
                // 若循环到最后一个td并且图标开关开启，则表示最后一个td为存放图标的空td，可跳过此次循环
                // if ((j === _tdLast) && withEcharts && thHtmlArr[_tdLast]) {
                //
                //     if (parseFloat(_stack.result) == _stack.result) {
                //         _td = '<td><a class="check_goEchart" href="javascript:;" for-echarts="' + _stack.param + '"></a></td>';
                //     }
                //
                //     tdHtmlArr[j] = _td;
                //     continue;
                // }

                _stack.index = null;
                _stack.min = null;
                _stack.max = null;
                _stack.value = null;

                // 遍历tds数据
                for (var s = 0, l = tds.length; s < l; s++) {

                    if (tds[s].nodeName == resultName) {
                        _stack.result = tds[s].text;
                    }

                    if (tds[s].nodeName == paramName) {
                        _stack.param = tds[s].text;
                    }

                    if (tds[s].nodeName == 'inspectionMin') {
                        _stack.min = tds[s].text;
                    }

                    if (tds[s].nodeName == 'inspectionMax') {
                        _stack.max = tds[s].text;
                    }

                    if (thHtmlArr[j] && j == parseInt(tds[s].index)) {
                        _td = '<td>' + tds[s].text + '</td>';

                        if (tds[s].nodeName == 'result') {
                            _stack.value = tds[s].text;
                            _stack.index = tds[s].index;
                        }
                    }

                }

                if (thHtmlArr[j]) {
                    tdHtmlArr[j] = _td;
                }

                if (_stack.index !== null) {

                    var __value = parseFloat(_stack.value);

                    if (_stack.min || _stack.max) {

                        _stack.min = parseFloat(_stack.min);
                        _stack.max = parseFloat(_stack.max);

                        if (__value < _stack.min) {
                            tdHtmlArr[_stack.index] = '<td class="status_low">' + __value + ' ↓</td>';
                        } else if (__value > _stack.max) {
                            tdHtmlArr[_stack.index] = '<td class="status_high">' + __value + ' ↑</td>';
                        }

                    }

                }
            }

            _html += tdHtmlArr.join('');

            _html += '</tr>';
        }

        _html += '</tbody></table>';

        return _html;
    };

    Module.normalLabelFormat = function (str) {
        if (typeof str === 'string') {
            var l = str.length;
            switch (l) {
                case 2:
                    return str.split('').join('&#12288;&#12288;');
                case 3:
                    return str.split('').join('&ensp;');
                default:
                    return str;
            }
        }
    };

    // Module.normalUl = function (data, withEcharts, empi, payLoadType, resultName, paramName) {
    //     if (!data) return '';
    //     var _dataTbody = Module.getValue(data.tableRowList);
    //     var trL = _dataTbody.length;
    //     var _ul = '';
    //     for (var k = 0; k < trL; k++) {
    //
    //         _ul += '<li class="hover" >' + // personId 取值和empi一致
    //             '<input class="vm" type="checkbox" onclick="initLisHistory(\'' + empi + '\', \'' + payLoadType + '\')">' +
    //             '<span class="vm">' + _dataTbody[k][0].text + '</span>' +
    //             '</li>';
    //
    //     }
    //     return _ul;
    // }

    Module.removeSpace = function (str) {
        return str.replace(/　/g, '').replace(/ /g, '');
    }

    Module.BacteriaLISBG = function (data) {

        var _html = '';
        var records = Module.getValue(data.bacTestList);

        _html = '<div class="check">' +
            '<div class="check_main">' +
            '<table class="table">' +
            '<tbody>';

        for (var i = 0, l = records.length; i < l; i++) {

            var moreInfo = records[i].more == "true" ? '<a class="check_more" href="javascript:;"></a>' : '';
            var moreColor = records[i].more == "true" ? 'class="text_red"' : '';
            var _value = Module.getValue(records[i].value) instanceof Array ? Module.getValue(records[i].value) : [Module.getValue(records[i].value)];

            for (var j = 0, vl = _value.length; j < vl; j++) {

                var firstTd = '';

                if (j === 0) {
                    firstTd = '<td width="50%" rowspan="' + _value.length + '">' + Module.getValue(records[i].item) + '</td>';
                }

                _html += '<tr>' +
                    firstTd +
                    '<td width="50%" ' + moreColor + '>' + Module.getValue(_value[j].xijun, _value[j]) + '</td>' +
                    '</tr>';
            }

        }

        _html += '</tbody></table></div></div>';

        return _html;

    };
})