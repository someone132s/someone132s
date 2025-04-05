/**
 * Created by lizige on 2019/1/25.
 */
var Const = {};
Const.divide = [];
Const.baseUrl = "/CCD/";
// Const.baseUrl = "http://10.168.199.147:9875/CCD/";
//Const.baseUrl="http://58.247.133.186:18081/CCD/";
Const.assayGroupMap = {};
Const.reportStatus = {};
Const.echartsLinkDisplay = true;
Const.patientDomain = {
    inHos: '2.16.840.1.113883.4.487.2.1.4',
    outHos: '2.16.840.1.113883.4.487.2.1.4.1',
    exam: '2.16.840.1.113883.4.487.2.1.4.5',
    emergency: '2.16.840.1.113883.4.487.2.1.4.7'
};
Const.bloodApplyUnit = {
    "血红蛋白": "g/L",
    "ALT": "m/L",
    "血小板": "*10^9/L",
    "APTT": "秒",
    "PT": "秒",
    "Fbg": "g/L"
};
Const.reportProps = {
    'FrontPage': {
        "nodes": ["//hisba1", "//HisBa3List", "//HisBa4List", "//HisBa5List", "//HisBa6List"],
        "parseModel": "0"
    },
    'BA_FrontPage': {
        "nodes": ["//BAVisit", "//BADiagosis", "//BAOperation", "//BABaby", "//Bavmxbazl"],
        "parseModel": "0"
    },
    'MinorOperationRec': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'OperationDiscussion': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'OperationSummary': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'OperationRec': {
        "nodes": ["//body", "//section"],
        "parseModel": "0"
    },
    'ProgressNote': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'ABW': {
        "nodes": ["//ABWEMR//EmrdocqrymasterView"],
        "parseModel": "0"
    },
    'BloodApply': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'DeathSummary': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'DischargeDiagCertificate': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'DischargeRecord': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'TalkRec': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'ConsultationBG': {
        "nodes": ["//paragraph"],
        "parseModel": "0"
    },
    'InchargeRecord': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'InchargeRecord24Hour': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'InchargeRecord24HourDeath': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'RECIPE': {
        "nodes": ["//MetCasDiagnose"],
        "parseModel": "0"
    },
    'MZBL': {
        "nodes": ["//CM_MEDICAL"],
        "parseModel": "0"
    },
    'WardRecord': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'ProgressNote.0002': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'PreoperativeInterviewRecord': {
        "nodes": ["//body"],
        "parseModel": "0"
    },
    'KT_RECIPE': {
        "nodes": ["//TmzysZhenDuanJiLu_lishi", "//structuredBody/component/section/patient"],
        "parseModel": "0"
    }
};
Const.report = {
    FP: {
        ifType: {
            "1": "是",
            "2": "否"
        },
        whetherType: {//通用
            "1": "无",
            "2": "有"
        },
        whetherInverse: {//通用
            "0": "无",
            "1": "有",
            "2": "无"
        },
        mostType: {//通用
            "0": "未做",
            "1": "符合",
            "2": "不符合",
            "3": "不肯定"
        },
        levelRome: {//通用
            "1": "I",
            "2": "II",
            "3": "III",
            "4": "IV",
            "5": "V"
        },
        fyclj: {//临床路径
            "1": "是临床路径病种，完成路径无变异",
            "2": "是临床路径病种，完成路径有变异",
            "3": "是临床路径病种，入路径后退出",
            "4": "是临床路径病种，应入路径而未入",
            "5": "是临床路径病种，不需入路径",
            "6": "不是临床路径病种"
        },
        frytj: {
            "1": "急诊",
            "2": "门诊",
            "3": "其他医疗机构转入",
            "9": "其他"
        },
        ffrom: {
            "1": "本区",
            "2": "本市",
            "3": "本省",
            "4": "外省",
            "5": "港澳台",
            "6": "外国"
        },
        fzdlx: {//诊断类型
            "1": "主要诊断",
            "2": "其他诊断",
            "3": "并发症",
            "4": "院内感染",
            "5": "损伤",
            "6": "病理诊断",
            "7": "过敏药",
            "A": "门急诊诊断",
            "B": "入院诊断"
        },
        frybq: {//入院病情
            "1": "有",
            "2": "临床未明确",
            "3": "情况不明",
            "4": "无"
        },
        fcyqk: {//出院情况
            "1": "治愈",
            "2": "好转",
            "3": "未愈",
            "4": "死亡",
            "5": "其他"
        },
        fjbfx: {//病例分型
            "1": "一般",
            "2": "急",
            "3": "疑难",
            "4": "危重"
        },
        fzltype: {//肿瘤分期类型
            "1": "P病理",
            "2": "C临床"
        },
        fszsj: {//死亡患者尸检
            "1": "是",
            "2": "否",
            "-": "非死亡"
        },
        fblood: {//血型
            "1": "A型",
            "2": "B型",
            "3": "O型",
            "4": "AB型",
            "5": "不详",
            "6": "未查"
        },
        frh: {//RH
            "1": "阴",
            "2": "阳",
            "3": "不详",
            "4": "未查"
        },
        fbaquality: {//病案质量
            "1": "甲",
            "2": "乙",
            "3": "丙",
            "4": "其他"
        },
        fifbc: {//B超
            "1": "☑B超",
            "2": "□B超"
        },
        fssjb: {//手术级别
            "1": "一级",
            "2": "二级",
            "3": "三级",
            "4": "四级"
        },
        fqktype: {//切口类型和愈合等级
            "1": "01/甲",
            "2": "01/乙",
            "3": "01/丙",
            "4": "01/其他",
            "5": "02/甲",
            "6": "02/乙",
            "7": "02/丙",
            "8": "02/其他",
            "9": "03/甲",
            "10": "03/乙",
            "11": "03/丙",
            "12": "03/其他",
            "13": "I/甲",
            "14": "I/乙",
            "15": "I/丙",
            "16": "I/其他",
            "17": "II/甲",
            "18": "II/乙",
            "19": "II/丙",
            "20": "II/其他",
            "21": "III/甲",
            "22": "III/乙",
            "23": "III/丙",
            "24": "III/其他"
        },
        fmazui: {//麻醉方式
            "1": "全麻",
            "2": "硬外",
            "3": "基础麻",
            "4": "基麻+局麻",
            "5": "局麻",
            "6": "腰硬联合麻",
            "7": "骶麻",
            "8": "臂丛",
            "9": "颈丛",
            "10": "表麻",
            "11": "静脉麻",
            "12": "气管麻",
            "13": "插管全麻",
            "14": "其它"
        },
        flyfs: {//离院方式
            "1": "医嘱离院",
            "2": "医嘱转院",
            "3": "医嘱转社区卫生服务机构/乡镇卫生院",
            "4": "非医嘱离院",
            "5": "死亡",
            "6": "其他"
        },
        flx: {//疗效
            "CR": "消失",
            "PR": "显效",
            "MR": "好转",
            "S": "不变",
            "P": "恶化",
            "NA": "未定"
        },
        fflfs: {//放疗方式
            "1": "根治性",
            "2": "姑息性",
            "3": "辅助性"
        },
        fflcs: {//放疗程式
            "1": "连续",
            "2": "间断",
            "3": "分段"
        },
        fflzz: {//放疗装置
            "1": "钴",
            "2": "直加",
            "3": "X 线",
            "4": "后装"
        },
        fhlfs: {//化疗方式
            "1": "根治性",
            "2": "姑息性",
            "3": "新辅助性",
            "4": "辅助性",
            "5": "新药试用",
            "6": "其它"
        },
        fhlff: {//化疗方法
            "1": "全化",
            "2": "动脉插管",
            "3": "胸腔注",
            "4": "腹腔注",
            "5": "髓注",
            "6": "其他"
        }
    }
};
Const.mjzbl_kvs = {
    "Complained": "主诉",
    "MedicalHistory": "病史",
    "AllergicHistory": "过敏史",
    "PhysicalExamination": "体格检查",
    "TreatmentAndExamination": "辅助检查",
    "PreliminaryDiagnosis": "初步诊断",
    "Handle": "处理",
    "Doctor": "医生签名",
    "VisitTime": "就诊时间"
};