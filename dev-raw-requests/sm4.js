/**
 * 国密SM4加密算法
 * 基于网上下载的sm4.js版本修改，网上版本有Number位溢出问题，所以加密结果不对，
 * 虽然自身能正常加解密，但不能与其它语言相互回加密秘
 * 主要是修改为用BigInteger来计算，参考Java版的SM4.java计算方式来改造
 * modify by dengwuping
 * @date 2018-10
 */
function SM4Context() { 
	this.mode = 1;  
	this.isPadding = true;  
	this.sk = new Array(32);
}

function SM4() {
	this.SM4_ENCRYPT = 1;
	this.SM4_DECRYPT = 0;
     
	this.S_BOX_TABLE = [0xd6,0x90,0xe9,0xfe,0xcc,0xe1,0x3d,0xb7,0x16,0xb6,0x14,0xc2,0x28,0xfb,0x2c,0x05,
            0x2b,0x67,0x9a,0x76,0x2a,0xbe,0x04,0xc3,0xaa,0x44,0x13,0x26,0x49,0x86,0x06,0x99,
            0x9c,0x42,0x50,0xf4,0x91,0xef,0x98,0x7a,0x33,0x54,0x0b,0x43,0xed,0xcf,0xac,0x62,
            0xe4,0xb3,0x1c,0xa9,0xc9,0x08,0xe8,0x95,0x80,0xdf,0x94,0xfa,0x75,0x8f,0x3f,0xa6,
            0x47,0x07,0xa7,0xfc,0xf3,0x73,0x17,0xba,0x83,0x59,0x3c,0x19,0xe6,0x85,0x4f,0xa8,
            0x68,0x6b,0x81,0xb2,0x71,0x64,0xda,0x8b,0xf8,0xeb,0x0f,0x4b,0x70,0x56,0x9d,0x35,
            0x1e,0x24,0x0e,0x5e,0x63,0x58,0xd1,0xa2,0x25,0x22,0x7c,0x3b,0x01,0x21,0x78,0x87,
            0xd4,0x00,0x46,0x57,0x9f,0xd3,0x27,0x52,0x4c,0x36,0x02,0xe7,0xa0,0xc4,0xc8,0x9e,
            0xea,0xbf,0x8a,0xd2,0x40,0xc7,0x38,0xb5,0xa3,0xf7,0xf2,0xce,0xf9,0x61,0x15,0xa1,
            0xe0,0xae,0x5d,0xa4,0x9b,0x34,0x1a,0x55,0xad,0x93,0x32,0x30,0xf5,0x8c,0xb1,0xe3,
            0x1d,0xf6,0xe2,0x2e,0x82,0x66,0xca,0x60,0xc0,0x29,0x23,0xab,0x0d,0x53,0x4e,0x6f,
            0xd5,0xdb,0x37,0x45,0xde,0xfd,0x8e,0x2f,0x03,0xff,0x6a,0x72,0x6d,0x6c,0x5b,0x51,
            0x8d,0x1b,0xaf,0x92,0xbb,0xdd,0xbc,0x7f,0x11,0xd9,0x5c,0x41,0x1f,0x10,0x5a,0xd8,
            0x0a,0xc1,0x31,0x88,0xa5,0xcd,0x7b,0xbd,0x2d,0x74,0xd0,0x12,0xb8,0xe5,0xb4,0xb0,
            0x89,0x69,0x97,0x4a,0x0c,0x96,0x77,0x7e,0x65,0xb9,0xf1,0x09,0xc5,0x6e,0xc6,0x84,
            0x18,0xf0,0x7d,0xec,0x3a,0xdc,0x4d,0x20,0x79,0xee,0x5f,0x3e,0xd7,0xcb,0x39,0x48];
            
//	var FK = [ 0xa3b1bac6, 0x56aa3350, 0x677d9197, 0xb27022dc ];
	//字符串方便转BigInteger，（为与Java端一致，第1、4位转为有符号，Java端是用int有符号进行异或）
	this.FK = ['-5c4e453a', '56aa3350', '677d9197', '-4d8fdd24'];
//	var CK = [0x00070e15,0x1c232a31,0x383f464d,0x545b6269,
//  		0x70777e85,0x8c939aa1,0xa8afb6bd,0xc4cbd2d9,
//  		0xe0e7eef5,0xfc030a11,0x181f262d,0x343b4249,
// 			0x50575e65,0x6c737a81,0x888f969d,0xa4abb2b9,
//			0xc0c7ced5,0xdce3eaf1,0xf8ff060d,0x141b2229,
//      	0x30373e45,0x4c535a61,0x686f767d,0x848b9299,
//      	0xa0a7aeb5,0xbcc3cad1,0xd8dfe6ed,0xf4fb0209,
//        	0x10171e25,0x2c333a41,0x484f565d,0x646b7279];
	this.CK = ['70e15', '1c232a31', '383f464d', '545b6269', 
			'70777e85', '-736c655f', '-57504943', '-3b342d27',
			'-1f18110b', '-3fcf5ef', '181f262d', '343b4249', 
			'50575e65', '6c737a81', '-77706963', '-5b544d47',
			'-3f38312b', '-231c150f', '-700f9f3', '141b2229',
			'30373e45', '4c535a61', '686f767d', '-7b746d67',
			'-5f58514b', '-433c352f', '-27201913', '-b04fdf7',
			'10171e25', '2c333a41', '484f565d', '646b7279'];
	
	this.getUlongBE = function(b, i) {
		var b1 = new BigInteger(String(b[i] & 0xff)).shiftLeft(24);
		var b2 = new BigInteger(String(b[i + 1] & 0xff)).shiftLeft(16);
		var b3 = new BigInteger(String(b[i + 2] & 0xff)).shiftLeft(8);
		var b4 = new BigInteger(String(b[i + 3] & 0xff)).and(new BigInteger("FFFFFFFF", 16));
	
		return b1.or(b2).or(b3).or(b4);
		//return (b[i] & 0xff) << 24 | ((b[i + 1] & 0xff) << 16) | ((b[i + 2] & 0xff) << 8) | (b[i + 3] & 0xff) & 0xffffffff;
	};

	this.putUlongBE = function(n, b, i) {
		b[i] = n.shiftRight(24).and(new BigInteger("0xFF", 16)).byteValue();
		b[i + 1] = n.shiftRight(16).and(new BigInteger("0xFF", 16)).byteValue();
		b[i + 2] = n.shiftRight(8).and(new BigInteger("0xFF", 16)).byteValue();
		b[i + 3] = n.and(new BigInteger("0xFF", 16)).byteValue();
// 		var t1=(0xFF & (n >> 24));
//     	var t2=(0xFF & (n >> 16));
//     	var t3=(0xFF & (n >> 8));
//    	var t4=(0xFF & (n));
//     	b[i] = t1>128?t1-256:t1;
//     	b[i + 1] = t2>128?t2-256:t2;
//     	b[i + 2] = t3>128?t3-256:t3;
//     	b[i + 3] = t4>128?t4-256:t4;    
	};
    
	this.rotl = function(x,  n) {
		//(x & 0xFFFFFFFF) << n;
		var b1 = x.and(new BigInteger("FFFFFFFF", 16)).shiftLeft(n);
		return b1.or(x.shiftRight(32 - n));
		//return this.SHL(x, n) | x >> (32 - n);
	};
    
	this.sm4Lt = function(ka) {
		var a = new Array(4);
		var b = new Array(4);
		this.putUlongBE(ka, a, 0);
		b[0] = this.sm4Sbox(a[0]);
		b[1] = this.sm4Sbox(a[1]);
		b[2] = this.sm4Sbox(a[2]);
		b[3] = this.sm4Sbox(a[3]);
		var bb = this.getUlongBE(b, 0);
		var c = bb.xor(this.rotl(bb, 2)).xor(this.rotl(bb, 10)).xor(this.rotl(bb, 18)).xor(this.rotl(bb, 24));

//		c = bb ^ this.rotl(bb, 2) ^ this.rotl(bb, 10) ^ this.rotl(bb, 18) ^ this.rotl(bb, 24);
		return c;
	};
	
	this.sm4F = function(x0, x1, x2, x3, rk) {
		return x0.xor(this.sm4Lt(x1.xor(x2).xor(x3).xor(rk)));
//		return x0 ^ this.sm4Lt(x1 ^ x2 ^ x3 ^ rk);
	};
	
	this.sm4CalciRK = function(ka) {
		var a = new Array(4);
		var b = new Array(4);
		this.putUlongBE(ka, a, 0);
		b[0] = this.sm4Sbox(a[0]);
		b[1] = this.sm4Sbox(a[1]);
		b[2] = this.sm4Sbox(a[2]);
		b[3] = this.sm4Sbox(a[3]);
		var bb = this.getUlongBE(b, 0);
		// rk = bb ^ this.rotl(bb, 13) ^ this.rotl(bb, 23);
		var rk = bb.xor(this.rotl(bb, 13)).xor(this.rotl(bb, 23));
		return rk;
	};   
     
	this.sm4Sbox = function(inch) {
		var i = inch & 0xFF;
		var retVal = this.S_BOX_TABLE[i];
		return retVal > 128 ? retVal - 256 : retVal;
	};
	
	this.sm4SetKeyEnc = function(ctx, key) {
		if (ctx == null) {
			alert("ctx is null!");
			return false;
		}
		
		ctx.mode = this.SM4_ENCRYPT;
		this.sm4SetKey(ctx.sk, key);

	};
	
	this.sm4SetKeyDec = function(ctx, key) {
		this.sm4SetKeyEnc(ctx, key);
		ctx.mode = this.SM4_DECRYPT;
		for (var i = 0; i < 16; i++) {
//			this.SWAP(ctx.sk, i);
			var t = ctx.sk[i];
			ctx.sk[i] = ctx.sk[(31 - i)];
			ctx.sk[(31 - i)] = t;
		}
	};
	
	this.sm4SetKey = function(SK, key) {
		var MK = new Array(4);// bint
		var k =  new Array(36);// bint
		MK[0] = this.getUlongBE(key, 0);
		MK[1] = this.getUlongBE(key, 4);
		MK[2] = this.getUlongBE(key, 8);
		MK[3] = this.getUlongBE(key, 12);

		k[0] = MK[0].xor(new BigInteger(this.FK[0], 16));//MK[0] ^  FK[0];
		k[1] = MK[1].xor(new BigInteger(this.FK[1], 16));//MK[1] ^  FK[1];
		k[2] = MK[2].xor(new BigInteger(this.FK[2], 16));//MK[2] ^  FK[2];
		k[3] = MK[3].xor(new BigInteger(this.FK[3], 16));//MK[3] ^  FK[3];

		for (var i = 0; i < 32; i++) {
			k[(i + 4)] = k[i].xor(this.sm4CalciRK(k[i + 1].xor(k[(i + 2)]).xor(k[(i + 3)]).xor(new BigInteger(this.CK[i], 16))));
//			k[(i + 4)] = (k[i] ^ this.sm4CalciRK(k[(i + 1)] ^ k[(i + 2)] ^ k[(i + 3)] ^ CK[i]));
 			SK[i] = k[(i + 4)];
		}
	};
    
	this.padding = function(input, mode) {
		if (input == null) {
			return null;
		}
		var ret = null;
		if (mode == this.SM4_ENCRYPT) {
			var p = parseInt(16 - input.length % 16);
			ret = input.slice(0);
			for (var i = 0; i < p; i++) {
				ret[input.length + i] = p;
			}
		} else {
			var p = input[input.length - 1];
			ret = input.slice(0, input.length - p);
		}
		return ret;
	};
	
	this.sm4OneRound = function(sk, input, output) {
		var i = 0;
		var ulbuf = new Array(36);
		ulbuf[0] = this.getUlongBE(input, 0);
		ulbuf[1] = this.getUlongBE(input, 4);
		ulbuf[2] = this.getUlongBE(input, 8);
		ulbuf[3] = this.getUlongBE(input, 12);
		while (i < 32) {
			ulbuf[(i + 4)] = this.sm4F(ulbuf[i], ulbuf[(i + 1)],
					ulbuf[(i + 2)], ulbuf[(i + 3)], sk[i]);
			i++;
		}
		
		this.putUlongBE(ulbuf[35], output, 0);
		this.putUlongBE(ulbuf[34], output, 4);
		this.putUlongBE(ulbuf[33], output, 8);
		this.putUlongBE(ulbuf[32], output, 12);
	};

	this.sm4CryptEcb = function(ctx, input) {
		if (input == null) {
			alert("input is null!");
		}
		if ((ctx.isPadding) && (ctx.mode == this.SM4_ENCRYPT)) {
			input = this.padding(input, this.SM4_ENCRYPT);
		}

		var i = 0;
		var length = input.length;
		var bous = new Array();
		for (; length > 0; length -= 16) {
			var out = new Array(16);
			var ins = input.slice(i * 16, (16 * (i + 1)));
			this.sm4OneRound(ctx.sk, ins, out)
			bous = bous.concat(out);
			i++;
		}

		var output = bous;
		if (ctx.isPadding && ctx.mode == this.SM4_DECRYPT) {
			output = this.padding(output, this.SM4_DECRYPT);
		}
		for (var i = 0; i < output.length; i++) {
			if (output[i] < 0) {
				output[i] = output[i] + 256;
			}
		}
		return output;
	};
        
	this.sm4CryptCbc = function(ctx, iv, input) {
		if (iv == null || iv.length != 16) {
			alert("iv error!");
		}

		if (input == null) {
			alert("input is null!");
		}

		if (ctx.isPadding && ctx.mode == this.SM4_ENCRYPT) {
			input = this.padding(input, this.SM4_ENCRYPT);
		}

		var i = 0;
		var length = input.length;
		var bous = new Array();
		if (ctx.mode == this.SM4_ENCRYPT) {
			var k = 0;
			for (; length > 0; length -= 16) {
				var out = new Array(16);
				var out1 = new Array(16);
				var ins = input.slice(k * 16, (16 * (k + 1)));

				for (i = 0; i < 16; i++) {
					out[i] = (ins[i] ^ iv[i]);
				}
				this.sm4OneRound(ctx.sk, out, out1);
				iv = out1.slice(0, 16);
				bous = bous.concat(out1);
				k++;
			}
		} else {
			var temp = [];
			var k = 0;
			for (; length > 0; length -= 16) {
				var out = new Array(16);
				var out1 = new Array(16);
				var ins = input.slice(k * 16, (16 * (k + 1)));
				temp = ins.slice(0, 16);
				this.sm4OneRound(ctx.sk, ins, out);
				for (i = 0; i < 16; i++) {
					out1[i] = (out[i] ^ iv[i]);
				}
				iv = temp.slice(0, 16);
				bous = bous.concat(out1);
				k++;
			}
		}

		var output = bous;
		if (ctx.isPadding && ctx.mode == this.SM4_DECRYPT) {
			output = this.padding(output, this.SM4_DECRYPT);
		}

		for (var i = 0; i < output.length; i++) {
			if (output[i] < 0) {
				output[i] = output[i] + 256;
			}
		}
		return output;
	};
}

function SM4Util() {
	var sm4 = new SM4();
	
	this.sm4Encrypt = function(key, text) {
		var ctx = new SM4Context();
		 var keyBytes=Str2Bytes(key);
		sm4.sm4SetKeyEnc(ctx, keyBytes);
		var encrypted = sm4.sm4CryptEcb(ctx, strToUtf8Bytes(text));
		return bytesToHex(encrypted);
	};
	
	this.sm4Decrypt = function(key, cipherText) {
		var ctx = new SM4Context();
		var keyBytes=Str2Bytes(key);
		sm4.sm4SetKeyDec(ctx, keyBytes);
		var encrypted = sm4.sm4CryptEcb(ctx, hexToBytes(cipherText));
		return bytesToUtf8Str(encrypted);
	};
	
	this.sm4EncryptCbc = function(key, iv, text) {
		var ctx = new SM4Context();
		var keyBytes = strToUtf8Bytes(key);
		var ivBytes= strToUtf8Bytes(iv) ;
		sm4.sm4SetKeyEnc(ctx, keyBytes);
		var encrypted = sm4.sm4CryptCbc(ctx, ivBytes, strToUtf8Bytes(text));  
		return bytesToHex(encrypted);
	};
	
	this.sm4DecryptCbc = function(key, iv, cipherText) {
		var ctx = new SM4Context();
		var keyBytes = strToUtf8Bytes(key);
		var ivBytes= strToUtf8Bytes(iv) ;
		sm4.sm4SetKeyDec(ctx, keyBytes);
		var encrypted = sm4.sm4CryptCbc(ctx, ivBytes, hexToBytes(cipherText));
		return bytesToUtf8Str(encrypted);
	};
}

//十六进制字符串转字节数组
function Str2Bytes(str){
	var pos = 0;
	var len = str.length;
	if(len %2 != 0){
		return null; 
	}
	len /= 2;
	var hexA = new Array();
	for(var i=0; i<len; i++){
	   var s = str.substr(pos, 2);
	   var v = parseInt(s, 16);
	   hexA.push(v);
	   pos += 2;
	}
	return hexA;
}
//字节数组转十六进制字符串
function Bytes2Str(arr){
	var str = "";
	for(var i=0; i<arr.length; i++){
	   var tmp = arr[i].toString(16);
	   if(tmp.length == 1){
		   tmp = "0" + tmp;
	   }
	  str += tmp;
	}
	return str;
}