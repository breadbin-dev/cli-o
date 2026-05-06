package clio.core.rest;

import java.io.IOException;
import java.time.LocalDateTime;

import clio.core.Collections;
import clio.core.CronSession;
import clio.core.Param;
import clio.core.Strings;
import org.apache.hc.client5.http.classic.HttpClient;
import org.apache.hc.client5.http.classic.methods.HttpDelete;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManager;
import org.apache.hc.core5.http.ClassicHttpRequest;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.apache.hc.core5.util.TimeValue;

public class RestClient {

    private final CloseableHttpClient client;

    private final String url;

    private final Param[] headers;
    private final CronSession session;

    public RestClient(String url, Param... headers) {
        this(url, null, headers);
    }

    public RestClient(String url, CronSession session, Param... headers) {
        this.session = session;

        if (!url.endsWith("/"))
            url += "/";
        this.url = url;
        this.headers = headers;
        System.setProperty("javax.net.ssl.trustStore", "/etc/pki/java/cacerts");

        var connManager = new PoolingHttpClientConnectionManager();
        connManager.setMaxTotal(1000);
        connManager.setDefaultMaxPerRoute(1000);

        client = HttpClients.custom()
                .setConnectionManager(connManager)
                .evictExpiredConnections()
                .evictIdleConnections(TimeValue.ofSeconds(10))
                .build();
    }

    private void checkSession() {
        if (session != null && session.isClosed(LocalDateTime.now()))
            throw new ConnectionException("Session outside of configured hours");
    }

    public <T> T post(String item, Object payload, Class<T> returnType, Param... params) {
        String payloadStr = Strings.toJson(payload);

        try {
            var request = new HttpPost(url(item, params));
            for (var header : headers)
                request.addHeader(header.name(), header.value());

            request.setEntity(new StringEntity(payloadStr, ContentType.APPLICATION_JSON));

            return execute(client, request, returnType);
        } catch (IOException e) {
            throw new ConnectionException(e);
        }
    }

    private String url(String item, Param... params) {
        var url = this.url + item;
        var paramsStr = String.join("&", Collections.map(params, Param::toUrlParam));
        if (!paramsStr.isEmpty())
            url += "?" + paramsStr;
        return url;
    }

    public <T> T get(String item, Class<T> type, String args, Param... params) {
        try {
            var request = new HttpGet(url(item, params));
            for (var header : headers)
                request.addHeader(header.name(), header.value());

            if (args != null)
                request.setEntity(new StringEntity(args));

            return execute(client, request, type);
        } catch (IOException e) {
            throw new ConnectionException(e);
        }
    }

    public <T> T delete(String item, Class<T> type, String args, Param... params) {
        try {
            var request = new HttpDelete(url(item, params));
            for (var header : headers)
                request.addHeader(header.name(), header.value());

            if (args != null)
                request.setEntity(new StringEntity(args));

            return execute(client, request, type);
        } catch (IOException e) {
            throw new ConnectionException(e);
        }
    }

    private <T> T execute(HttpClient client, ClassicHttpRequest request, Class<T> type) throws IOException {

        checkSession();

        String response;

        try {
            response = client.execute(request, r -> {
                var code = r.getCode();
                if (code != 200) {
                    var reason = r.getReasonPhrase();
                    if (!Strings.hasValue(reason)) {
                        try {
                            reason = Strings.readStream(r.getEntity().getContent());
                        } catch (Exception ex) {
                            // pass
                        }
                    }
                    throw new ResponseException(code, reason);
                }
                return EntityUtils.toString(r.getEntity());
            });
        }
        catch (Throwable e) {
            if (e instanceof ConnectionException)
                throw (ConnectionException) e;
            throw new ConnectionException(e);
        }


        try {
            if (type == String.class)
                return (T) response;
            else {
                if (Strings.hasValue(response))
                    return Strings.readJson(response, type);
                else
                    throw new ConnectionException("Empty Response");
            }
        }
        catch (Throwable e) {
            if (e instanceof ConnectionException)
                throw (ConnectionException) e;
            throw new DeserializationException(e);
        }
    }
}