// n = {
//     method: "get"
// }
// r = Math.round(Date.now() / 1e3) + (e.expires || 1800)
// o = r.toString()
// a = {}

// getResourcePath = function(t) {
//     return this.bucket ? "/".concat(this.bucket, "/").concat(t) : "/".concat(t)
// }

// createSign = function(t, e, n, r) {
//     var o, i = this, a = h.createHmac("sha1", this.accessKeySecret), c = [(null === (o = n.method) || void 0 === o ? void 0 : o.toUpperCase()) || "GET", n["Content-MD5"] || "", n["Content-Type"], r || n["x-oss-date"]];
//     return Object.keys(n).forEach((function(t) {
//         0 === t.indexOf(i.ossPrefix) && c.push("".concat(t, ":").concat(n[t]))
//     }
//     )),
//     c.push(this.createCanonicalizedResource(t, e)),
//     a.update(s.Buffer.from(c.join("\n"), this.headerEncoding)).digest("base64")
// }

// s = createSign(i, a, n, o)
                                
// function t(t) {
//     this.region = "oss-ap-southeast-1",
//     this.accessKeyId = "",
//     this.accessKeySecret = "",
//     this.stsToken = "",
//     this.endpoint = "oss-accelerate.aliyuncs.com",
//     this.bucket = "mix-ads",
//     this.headerEncoding = "utf-8",
//     this.refreshSTSTokenInterval = 6e4,
//     this.refreshTime = 0,
//     this.ossPrefix = "x-oss",
//     // this.accessKeyId = t.accessKeyId,
//     // this.accessKeySecret = t.accessKeySecret,
//     // this.stsToken = t.stsToken,
//     this.refreshSTSTokenInterval = 3e5,
//     // this.refreshSTSToken = t.refreshSTSToken,
//     this.refreshTime = Date.now()
// }

// 模拟初始化一个签名器类
function Signer() {
    this.region = "oss-ap-southeast-1";
    this.endpoint = "oss-accelerate.aliyuncs.com";
    this.bucket = "mix-ads";
    this.headerEncoding = "utf-8";
    this.ossPrefix = "x-oss";

    // ❗这些密钥应该是从服务器返回或页面中动态获取的，你需要手动补上
    this.accessKeyId = "";       // 必填
    this.accessKeySecret = "";   // 必填
    this.stsToken = "";          // 可选
}

// 获取资源路径：拼接 bucket + object key
Signer.prototype.getResourcePath = function (objectKey) {
    return this.bucket ? `/${this.bucket}/${objectKey}` : `/${objectKey}`;
};

// Canonicalized Resource 生成（用于构造签名原始字符串）
Signer.prototype.createCanonicalizedResource = function (path, queryParams) {
    let result = `${path}`;
    let prefix = "?";

    Object.keys(queryParams)
        .sort()
        .forEach((key) => {
            result += prefix + key;
            if (queryParams[key]) result += "=" + queryParams[key];
            prefix = "&";
        });

    return result;
};

// 创建 OSS 签名
Signer.prototype.createSign = function (path, queryParams, headers, dateStr) {
    const hmac = require("crypto").createHmac("sha1", this.accessKeySecret);
    const method = (headers.method || "GET").toUpperCase();
    const contentMD5 = headers["Content-MD5"] || "";
    const contentType = headers["Content-Type"] || "";
    const date = dateStr || headers["x-oss-date"];

    // 构造签名前缀内容
    const lines = [method, contentMD5, contentType, date];

    // 添加所有以 x-oss- 开头的 header
    Object.keys(headers).forEach((key) => {
        if (key.startsWith(this.ossPrefix)) {
            lines.push(`${key}:${headers[key]}`);
        }
    });

    lines.push(this.createCanonicalizedResource(path, queryParams));

    const signStr = lines.join("\n");
    return hmac.update(Buffer.from(signStr, this.headerEncoding)).digest("base64");
};

const signer = new Signer();

const objectKey = "ads/sample.jpg";
const path = signer.getResourcePath(objectKey);

const queryParams = {
};

const headers = {
    method: "get"
}

const expires = 1800;
const expiryTimestamp = Math.round(Date.now() / 1e3) + (1800);
const signature = signer.createSign(path, queryParams, headers, expiryTimestamp.toString());

console.log("Signature:", signature);
console.log("Current Timestamp:", expiryTimestamp - 1800);
