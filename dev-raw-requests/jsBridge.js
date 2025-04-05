/**
 * Created by lizige on 2018/6/11.
 */
(function (win) {

    var ua = navigator.userAgent;
    var hasOwn = {}.hasOwnProperty;

    function getQueryString(name) {
        var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i');
        var r = window.location.search.substr(1).match(reg);
        if (r !== null) return unescape(r[2]);
        return null;
    }

    function isAndroid() {
        return ua.indexOf('Android') > 0;
    }

    function isIOS() {
        return /(iPhone|iPad|iPod)/i.test(ua);
    }

    function setupWebViewJavascriptBridge(callback) {
        if (win.WebViewJavascriptBridge) {
            return callback(WebViewJavascriptBridge);
        } else {
            callback(null);
        }
        if (win.WVJBCallbacks) {
            return win.WVJBCallbacks.push(callback);
        } else {
            //$.alert("WVJBCallbacks");
        }
        win.WVJBCallbacks = [callback];
        var WVJBIframe = document.createElement('iframe');
        WVJBIframe.style.display = 'none';
        WVJBIframe.src = 'https://__bridge_loaded__';
        document.documentElement.appendChild(WVJBIframe);
        setTimeout(function () {
            document.documentElement.removeChild(WVJBIframe)
        }, 0)
    }

    var mobile = {
        /**
         *通过bridge注册js回调函数
         * @param method
         * @param callbackData 返回的数据
         */
        registerIOSHandler: function (method) {
            if (isIOS()) {
                setupWebViewJavascriptBridge(function (bridge) {
                    if (bridge) {
                        bridge.registerHandler(method, function (data, responseCallback) {
                            //$.alert("调用方法" + method + "  返回的参数" + data);
                            jsBridgeMethod[method](data);
                            if (responseCallback) {
                                responseCallback(callbackData);
                            }
                        })
                    }
                })
            }
        },

        /**
         *通过bridge调用app端的方法
         * @param method
         * @param params
         * @param callback
         */
        callAppRouter: function (method, params, callback) {
            if (isIOS()) {
                setupWebViewJavascriptBridge(function (bridge) {
                    if (bridge) {
                        bridge.callHandler(method, params, function (result) {
                            //var resultObj = null;
                            //var errorMsg = null;
                            //if (typeof(result) !== 'undefined' && result !== 'null' && result !== null) {
                            //    resultObj = JSON.parse(result);
                            //    if (resultObj) {
                            //        resultObj = resultObj['result'];
                            //    }
                            //}
                            callback(result);
                        });
                    } else {
                        //$.alert("版本过旧，请升级到最新版本！", function () {
                        callback(null);
                        //});
                    }
                })
            } else if (isAndroid()) {

                //生成回调函数方法名称
                //var cbName = 'CB_' + Date.now() + '_' + Math.ceil(Math.random() * 10);
                ////挂载一个临时函数到window变量上，方便app回调
                //win[cbName] = function (result) {
                //    var resultObj;
                //    if (typeof(result) !== 'undefined' && result !== null) {
                //        resultObj = JSON.parse(result)['result'];
                //    }
                //    callback(resultObj);
                //    //回调成功之后删除挂载到window上的临时函数
                //    delete win[cbName];
                //};
                // 安卓桥接需要初始化
                if (isAndroid() && !win.androidInit) {
                    win.androidInit = true;
                    // eslint-disable-next-line no-unused-vars
                    // win.WebViewJavascriptBridge.init((message, responseCallback) => { });
                    if (win.WebViewJavascriptBridge && typeof win.WebViewJavascriptBridge.init === 'function') {
                        win.WebViewJavascriptBridge.init((message, responseCallback) => { });
                    } else {
                        console.error('WebViewJavascriptBridge 或 init 方法未定义');
                    }
                }
                if (win.bridge) {
                    try {
                        //hasOwn.call(win.bridge,method,params);
                        if (win.bridge.hasOwnProperty(method)) {
                            if (params != "") {
                                callback(win.bridge[method](params));
                            } else {
                                callback(win.bridge[method]());
                            }
                        } else {
                            // $.alert("请在app中打开，或者版本够旧，请升级到最新版本", function () {
                            // callback(null);
                            // });
                            win.bridge.callHandler(method, params, function (result) {
                                callback(result);
                            });
                        }
                    } catch (e) {
                        callback(null);
                    }

                } else if (win.WebViewJavascriptBridge) {

                    try {
                        //hasOwn.call(win.bridge,method,params);
                        if (win.WebViewJavascriptBridge.hasOwnProperty(method)) {
                            if (params != "") {
                                callback(win.WebViewJavascriptBridge[method](params));
                            } else {
                                callback(win.WebViewJavascriptBridge[method]());
                            }
                        } else {
                            win.WebViewJavascriptBridge.callHandler(method, params, function (result) {
                                callback(result);
                            });
                        }
                    } catch (e) {
                        callback(null);
                    }
                } else {
                    callback(null);
                }
            }
        },
        /**
         *通过bridge调用js端的方法
         * @param method 方法名 openInfo:会诊资料 openMembers:与会人员 openList:返回会诊列表
         * @param params 参数 会诊ID：ID 等／json格式
         * @param callback 回调方法名
         */
        callJsRouter: function (method, params, callbackName) {

            if (jsBridgeMethod[method]) {
                jsBridgeMethod[method](params);
            } else {
                // $.alert("前端没有定义js接口:" + method);
                console.log("前端没有定义js接口:" + method);
            }
            if (callbackName) {
                console.log("暂未实现回调" + callbackName);
            }
        }
    };

    //将mobile对象挂载到window全局
    win.androidInit = false; // 安卓桥接需要初始化
    win.jsBridge = mobile;
    win.isAndroid = isAndroid();
    win.isIOS = isIOS();
})(window);