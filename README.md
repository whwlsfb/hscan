# HScan (web health/alive scan)

用于网站状况检测、通知

## 功能

用于检测网站状态发生异常时配合[Server酱(方糖推送)](http://sc.ftqq.com/)推送至负责人的微信的脚本，支持模拟GET、POST、HEAD请求。

### 检测机制

1. 可否连接（L3层异常）

   通过主动发起连接到Web Server，如果无法建立连接即断定为异常。

2. HTTP状态码

   主动发起请求，根据HTTP回应头中的状态码跟配置文件中相应字段进行对比，状态码异常及判断为异常。

3. HTML正文

   主动发起请求，根据HTTP正文中的HTML是否包含/不包含指定字符串，以此判断是否为异常。

### 推送机制

1. [Server酱](http://sc.ftqq.com/)推送。
2. [PushBear](http://pushbear.ftqq.com)推送组推送。

