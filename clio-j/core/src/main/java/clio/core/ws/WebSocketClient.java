package clio.core.ws;

import clio.core.*;
import jakarta.websocket.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static clio.core.Strings.f;

public class WebSocketClient extends Endpoint implements MessageHandler.Whole<String>, Disposable {

    private static final Logger log = LoggerFactory.getLogger(WebSocketClient.class);

    private final SubscriptionFuture<WebSocketClient> webSocket = new SubscriptionFuture<>();
    private final SubscriptionFuture<String> disposed = new SubscriptionFuture<>();

    private final String url;
    private final String token;
    private final Subscription<String> handler;

    private volatile Session session = null;

    public WebSocketClient(String url, String token, Subscription<String> handler) {
        this.url = url;
        this.token = token;
        this.handler = handler;
    }

    public SubscriptionFuture<WebSocketClient> subscribe() {
        try {
            var conf = new ClientEndpointConfig.Configurator() {
                @Override
                public void beforeRequest(Map<String, List<String>> headers) {
                    headers.put("Authorization", Collections.singletonList("Token " + token));
                }
            };
            var epConf = ClientEndpointConfig.Builder.create().configurator(conf).build();
            var container = ContainerProvider.getWebSocketContainer();
            container.connectToServer(this, epConf, URI.create(url));
        } catch (Exception ex) {
            throw new RuntimeException("Problem connecting: " + url, ex);
        }
        return webSocket;
    }

    public SubscriptionFuture<String> awaitDispose() {
        return disposed;
    }

    @Override
    public void onMessage(String message) {
        log.debug(f("Received message: {}", message));
        handler.accept(null, message);
    }

    public void send(String message) {
        var session = this.session;
        if (session == null)
            throw new SocketClosed(f("[{}] session closed", url));
        try {
            session.getBasicRemote().sendText(message);
        } catch (IOException ex) {
            throw new RuntimeException(f("[{}] problem sending message", url), ex);
        }
    }

    @Override
    public void onOpen(Session session, EndpointConfig config) {
        log.info(f("[{}] connected", url));
        this.session = session;
        session.addMessageHandler(this);
        this.webSocket.onResult(this);
    }

    @Override
    public void onClose(Session session, CloseReason reason) {
        var msg = f("{}({})", reason.getCloseCode(), reason.getReasonPhrase());

        log.warn(f("[{}] disconnected : {}", url, msg));
        this.session = null;
        this.webSocket.cancel(true);
        this.handler.safeOnError("session", "Closed [" + msg + "]");
        dispose(msg);
    }

    @Override
    public void onError(Session session, Throwable ex) {
        var msg = Exceptions.msg(ex);

        log.warn(f("[{}] received err: {}", url,  msg));
        this.webSocket.cancel(true);
        this.handler.safeOnError("session", ex);
        dispose(msg);
    }

    private void dispose(String msg) {
        this.handler.safeClose();
        this.disposed.onResult(msg);
    }

    @Override
    public void close() {
        dispose("disposed");

        var session = this.session;
        this.session = null;

        if (session != null) {
            try {
                session.removeMessageHandler(this);
                session.close();
            } catch (Throwable ex) {
                log.warn(f("[{}] problem closing session", url), ex);
            }
        }
    }
}
