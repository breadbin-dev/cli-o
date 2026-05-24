package clio.router;

import io.undertow.server.HttpServerExchange;
import io.undertow.util.Headers;
import io.undertow.util.HttpString;
import clio.core.Collections;
import clio.core.Strings;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.nio.charset.Charset;
import java.util.Map;

import static clio.core.Strings.f;

public class Request {
    private static final Logger log = LogManager.getLogger();

    private final HttpServerExchange exchange;
    private final Map<String, Object> options;

    public Request(HttpServerExchange exchange) {
        this.exchange = exchange;
        this.options = Collections.map(exchange.getQueryParameters(), (k, v) -> v.size() == 1 ? v.getFirst() : v);
    }

    @Override
    public String toString() {
        return "Request[exchange=" + exchange.getRequestPath() + "]";
    }

    public HttpServerExchange exchange() {
        return this.exchange;
    }

    @SuppressWarnings("unchecked")
    public <T> T getOption(String key) {
        return (T)options.get(key);
    }

    @SuppressWarnings("unchecked")
    public <T> T ensureOption(String key) {
        return (T)Collections.ensure(options, key);
    }

    public <T> void setOption(String key, T value) {
        options.put(key, value);
    }

    public String username() {
        return ensureOption("username");
    }

    public void sendWelcome(String title, String msg) {
        exchange.getResponseSender().send(f("<html><head><title>{}</title></head><body>{}</body></html>", title, msg));
    }

    public void sendNotFound() {
        send(404, "Not Found");
    }

    public void sendErr(String msg) {
        send(500, msg);
    }

    public void sendOK() {
        send(200, "OK");
    }

    public void sendText(String text) {
        send(text, "text/html");
    }

    public void sendJson(String json) {
        send(json, "application/json");
    }

    public void sendNoToken() {
        send(498, "Invalid Token");
    }

    public void sendUnauthorized() {
        send(401, "Unauthorized");
    }

    public void sendUnauthorized(String msg) {
        send(401, msg);
    }

    public void send(int code, String message) {
        setAccess();
        this.exchange.setStatusCode(code);
        this.exchange.setReasonPhrase(message);
        this.exchange.endExchange();
        log.debug("{} sent [{}]: {}", this, code, message);
    }

    public void send(String data, String contentType) {
        setAccess();
        var buf = Charset.defaultCharset().encode(data);
        var len = buf.remaining();
        var headers = exchange.getResponseHeaders();
        headers.put(Headers.CONTENT_LENGTH, Integer.toString(len));
        headers.put(Headers.CONTENT_TYPE, contentType);
        exchange.getResponseSender().send(buf);
        exchange.endExchange();
        log.debug("{} sent [{}]: {} bytes", this, contentType, len);
    }

    private void setAccess() {
        var headers = exchange.getResponseHeaders();
        headers.put(new HttpString("Access-Control-Allow-Origin"), "*");
        headers.put(new HttpString("Access-Control-Allow-Headers"), "Content-Type,Authorization");
        headers.put(new HttpString("Access-Control-Allow-Methods"), "GET,PUT,POST,DELETE,OPTIONS");
    }

    public boolean isOptions() {
        return exchange.getRequestMethod().equalToString("OPTIONS");
    }

    public String text() {
        try (var ignored = exchange.startBlocking()) {
            return Strings.readStream(exchange.getInputStream());
        } catch (IOException ex) {
            throw new RuntimeException("Problem reading request: " + this, ex);
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, String> textAsMap() {
        return Strings.readJson(text(), Map.class);
    }

    public String getToken() {
        var values = exchange.getRequestHeaders().get("Authorization");
        if (values != null && values.size() == 1) {
            var str = values.getFirst();
            if (str.startsWith("Bearer "))
                return str.substring(7);
            if (str.startsWith("Token "))
                return str.substring(6);
        }
        return null;
    }

    public void dispatch() {
        this.exchange.dispatch(() -> {}); // posting to another thread
    }
}
