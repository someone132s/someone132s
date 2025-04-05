//二进制数组转16进掉
function bytesToHex(arr) {
	var str = "";
	for (var i = 0; i < arr.length; i++) {
		str += (0x0100 + (arr[i] & 0x00FF)).toString(16).substring(1);
	}
	return str;
};
	
//16进掉转二进制数组
function hexToBytes(str) {
	var arr = [];
	var hexStrLength = str.length;
	for (var i = 0; i < hexStrLength; i += 2) {
		arr[arr.length] = parseInt(str.substr(i, 2), 16)
	}
	return arr;
};
	
//字符转UTF-8的二进制数组
function strToUtf8Bytes(str) {
	var bytes = new Array();
	var len, c;
	len = str.length;
	for (var i = 0; i < len; i++) {
		c = str.charCodeAt(i);
		if (c >= 0x010000 && c <= 0x10FFFF) {
			bytes.push(((c >> 18) & 0x07) | 0xF0);
			bytes.push(((c >> 12) & 0x3F) | 0x80);
			bytes.push(((c >> 6) & 0x3F) | 0x80);
			bytes.push((c & 0x3F) | 0x80);
		} else if (c >= 0x000800 && c <= 0x00FFFF) {
			bytes.push(((c >> 12) & 0x0F) | 0xE0);
			bytes.push(((c >> 6) & 0x3F) | 0x80);
			bytes.push((c & 0x3F) | 0x80);
		} else if (c >= 0x000080 && c <= 0x0007FF) {
			bytes.push(((c >> 6) & 0x1F) | 0xC0);
			bytes.push((c & 0x3F) | 0x80);
		} else {
			bytes.push(c & 0xFF);
		}
	}
	return bytes;
};
	
//二进制数组转UTF-8的字符
function bytesToUtf8Str(arr) {
	try {
		var str = '', _arr = arr;
		for (var i = 0; i < _arr.length; i++) {
			var one = _arr[i].toString(2), v = one.match(/^1+?(?=0)/);
			if (v && one.length == 8) {
				var bytesLength = v[0].length;
				var store = _arr[i].toString(2).slice(7 - bytesLength);
				for (var st = 1; st < bytesLength; st++) {
					store += _arr[st + i].toString(2).slice(2);
				}
				str += String.fromCharCode(parseInt(store, 2));
				i += bytesLength - 1;
			} else {
				str += String.fromCharCode(_arr[i]);
			}
		}
		return str;
	} catch(e) {
		alert("转UTF8出错，非UTF8的二进制数组");	
	}
};

function clearArray(destinationArray, destinationIndex, length) {
    for (elm in destinationArray) {
        destinationArray[elm] = null
    }
};

function copyArray(sourceArray, sourceIndex, destinationArray, destinationIndex, length) {
    var cloneArray = sourceArray.slice(sourceIndex, sourceIndex + length);
    for (var i = 0; i < cloneArray.length; i++) {
        destinationArray[destinationIndex] = cloneArray[i];
        destinationIndex++
    }
};