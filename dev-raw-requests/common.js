/**
 * Created by lizige on 08/04/2018.
 */
$(".weui-icon-back").parent().click(function () {
    history.back();
});
var common = {
    getNow: function () {
        return this.getNextDay(0);
    },
    getNextDay: function (AddDayCount) {
        var dd = new Date();
        dd.setDate(dd.getDate() + AddDayCount);//获取AddDayCount天后的日期
        var y = dd.getFullYear();
        var m = dd.getMonth() + 1;//获取当前月份的日期
        if (m < 10) {
            m = '0' + m;
        }
        var d = dd.getDate();
        if (d < 10) {
            d = '0' + d;
        }
        return y + "-" + m + "-" + d;
    },
    transDateInterval: function (beginTimeStr) {
        var startDateStr = this.dateFormart(beginTimeStr, "");
        var startTime = new Date(Date.parse(startDateStr.split(" ")[0].replace(/-/g, "/")));
        startTime.setHours(startDateStr.split(" ")[1].split(":")[0]);
        startTime.setMinutes(startDateStr.split(" ")[1].split(":")[1]);
        startTime.setSeconds(startDateStr.split(" ")[1].split(":")[2]);
        var dates = Math.floor((new Date().getTime() - startTime.getTime()) / (1000 * 60 * 60 * 24));
        return dates;
    },
    getQueryString: function (name) {
        var url = location.search; //获取url中"?"符后的字串
        if (url.indexOf("?") != -1) {
            var str = url.substr(1);
            strs = str.split("&");
            for (var i = 0; i < strs.length; i++) {
                var key = strs[i].split("=")[0];
                var value = strs[i].split("=")[1];
                if (key == name) {
                    return value;
                }
            }
        }
        return "";
    }, canNewLine: function (str) {
        return str.replace((new RegExp("\r\n", "gm")), "<br>");
    },
    /*替换所有字符串*/
    replace: function (str, a, b) {
        return str.replace((new RegExp(a, "gm")), b);
    },
    /*如果文字太长则只截取num长度*/
    substr: function (str, num) {
        var out = str;
        if (str.length > num) {
            out = str.substr(str, num) + "...";
        }
        return out;
    },
    /*如果匹配则添加突出颜色*/
    findCurUser: function (str, userName) {
        var out = str;
        if (str.length > 0 && userName && userName.length > 0) {
            out = str.replace(userName, "<span class='text-red'>" + userName + "</span>");
        }
        return out;
    },
    /*补0*/
    preZero: function (n) {
        return n < 10 ? "0" + n : n;
    },
    dateFormart: function (str, formartStr) {
        if (str != "" && str.length == 14) {
            var year = str.substring(0, 4);
            var month = str.substring(4, 6);
            var day = str.substring(6, 8);
            var hour = str.substring(8, 10);
            var minutes = str.substring(10, 12);
            var second = str.substring(12, 14);
            if (formartStr == "yyyy-MM-dd") {
                return year + "-" + month + "-" + day;
            } else if (formartStr == "yyyy年MM月dd日") {
                return year + "年" + month + "月" + day + "日";
            } else {
                return year + "-" + month + "-" + day + " " + hour + ":" + minutes + ":" + second;
            }
        } else {
            return str;
        }
    },
    addWaterMarker: function (str) {
        var can = document.createElement('canvas');
        var body = document.body;
        body.appendChild(can);
        can.width = 100; //画布的宽
        can.height = 120;//画布的高度
        can.style.display = 'none';
        var cans = can.getContext('2d');
        cans.rotate(-40 * Math.PI / 180); //画布里面文字的旋转角度
        cans.font = "16px Microsoft JhengHei"; //画布里面文字的字体
        cans.fillStyle = "rgba(221, 221, 221, 0.50)";//画布里面文字的颜色
        cans.textAlign = 'left'; //画布里面文字的水平位置
        cans.textBaseline = 'Middle'; //画布里面文字的垂直位置
        cans.fillText(str, can.width / 10, can.height / 2); //画布里面文字的间距比例
        body.style.backgroundImage = "url(" + can.toDataURL("image/png") + ")"; //把画布插入到body中
    }
}

$(function () {
    $.modal.prototype.defaults["title"] = "温馨提示";
    $.ajaxSetup({
        timeout: 30000,
        dataType: 'json',
        beforeSend: function(xhr, settings){
            const params = localStorage.getItem('jsBridgeHeaders')? JSON.parse(localStorage.getItem('jsBridgeHeaders')) : null
            if(params){
              xhr.setRequestHeader("X-Device-Model", params.equipmentType);
              xhr.setRequestHeader("X-OsType", params.osType);
              xhr.setRequestHeader("X-App-Version", params.appVersion || params.version);
              xhr.setRequestHeader("X-Device-Id", params.deviceId);
              xhr.setRequestHeader("X-Device-Name", params.deviceName);
              xhr.setRequestHeader("X-Device-Version", params.deviceVersion);
            }
        },
        error: function (jqXHR, textStatus) {
            $.hideLoading();
            $.alert("连接超时,请检查网络或稍后重试");
            return false;
        }
    });
    $("input[type='password']").bind("cut copy paste", function () {
        return false;
    })
    // document.addEventListener('touchmove', function (evt) {
    //     evt.preventDefault();
    // });
    //
    // document.addEventListener('touchmove', function (evt) {
    //     evt.preventDefault();
    // });
})