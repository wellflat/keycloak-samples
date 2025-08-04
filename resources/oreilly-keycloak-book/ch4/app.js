var express = require('express');
var app = express();
var stringReplace = require('string-replace-middleware');

var KC_URL = process.env.KC_URL || "http://trigkey:8080";
var SERVICE_URL = process.env.SERVICE_URL || "http://trigkey:3000/secured";

app.use(stringReplace({
   'SERVICE_URL': SERVICE_URL,
   'KC_URL': KC_URL
}));
app.use(express.static('.'))

app.get('/', function(req, res) {
    res.render('index.html');
});


app.listen(8000, '0.0.0.0', () => {
    console.log('Example app listening on port 8000!');
});
