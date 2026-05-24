package clio.router;

import io.undertow.websockets.WebSocketConnectionCallback;
import io.undertow.websockets.WebSocketProtocolHandshakeHandler;
import io.undertow.websockets.core.*;
import io.undertow.websockets.spi.WebSocketHttpExchange;
import clio.core.Disposable;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.util.function.Consumer;

import static io.undertow.Handlers.websocket;
import static clio.core.Strings.f;

public class Socket extends AbstractReceiveListener implements WebSocketConnectionCallback, WebSocketCallback<Void>, Disposable {

    private static final Logger log = LogManager.getLogger(Socket.class);

    private final String name;
    private final Disposable closer;
    private final Consumer<String> listener;
    private final WebSocketProtocolHandshakeHandler handshake;

    private WebSocketChannel channel;
    private boolean closed;

    public Socket(String name, Disposable closer, Consumer<String> listener) {
        this.name = name;
        this.closer = closer;
        this.listener = listener;
        this.handshake = websocket(this);
    }

    @Override
    public String toString() {
        return "Socket[" + name + "]";
    }
    
    public void send(String msg) {
        WebSockets.sendText(msg, channel, this);
    }

    public boolean isOpen() {
        synchronized (this) {
            return channel != null && channel.isOpen() && !closed;
        }
    }

    public boolean isClosed() {
        synchronized (this) {
            return channel != null && (closed || !channel.isOpen());
        }
    }

    public String name() {
        return name;
    }

    public Socket handle(Request req) {
        try {
            handshake.handleRequest(req.exchange());
            return this;
        } catch (Exception ex) {
            throw new RuntimeException(f("{} problem on websocket handshake: {}", this, req), ex);
        }
    }

    @Override
    public void onConnect(WebSocketHttpExchange exchange, WebSocketChannel channel) {
        synchronized (this) {
            this.channel = channel;
        }
        channel.addCloseTask(task -> close());
        channel.getReceiveSetter().set(this);
        channel.resumeReceives();
    }

    @Override
    protected void onFullTextMessage(WebSocketChannel channel, BufferedTextMessage message) throws IOException {
        listener.accept(message.getData());
    }

    @Override
    public void complete(WebSocketChannel webSocketChannel, Void unused) {

    }

    @Override
    public void onError(WebSocketChannel webSocketChannel, Void unused, Throwable ex) {
        log.error("{} problem on channel", this, ex);
        close();
    }

    @Override
    public void close() {
        boolean doClose;
        synchronized (this) {
            doClose = !closed;
            closed = true;
        }
        if (doClose)
            this.closer.close();
    }
}
