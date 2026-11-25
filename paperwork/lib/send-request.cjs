// Send one HTTP request and resolve its status and whole body text, so a relay run reads a reply in one await.
const http = require("http");

function request(method, url, { headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    const sent = http.request(url, { method, headers }, (response) => {
      let text = "";
      response.on("data", (chunk) => { text += chunk; });
      response.on("end", () => resolve({ status: response.statusCode, text }));
    });
    sent.on("error", reject);
    sent.end(body);
  });
}

module.exports = { request };
