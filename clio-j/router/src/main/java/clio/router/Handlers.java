package clio.router;

import io.undertow.server.HttpServerExchange;
import clio.core.Exceptions;
import clio.core.NamedThreads;
import clio.core.Strings;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

public class Handlers implements io.undertow.server.HttpHandler {

    private static final Logger log = LogManager.getLogger(Handlers.class);

    private final Map<String, Handler> handlers = new HashMap<>();

    private final Executor executor;
    private final TokenStore tokens;

    public Handlers(TokenStore tokens) {
        this.executor = Executors.newFixedThreadPool(20, new NamedThreads("Requests"));
        this.tokens = tokens;
    }

    public void addHandler(String root, Handler handler) {
        handlers.put(root, handler);
    }

    public Executor executor() {
        return executor;
    }

    @Override
    public void handleRequest(HttpServerExchange exchange) {
        var path = Strings.strip(exchange.getRelativePath(), "/").split("/");
        var root = path.length > 0 ? path[0] : "";
        var req = new Request(exchange);

        if ("".equals(root)) {
            req.sendWelcome("Router", "Welcome stranger, although you appear lost");
        } else if (req.isOptions()) {
            req.sendOK();
        } else {
            var handler = handlers.get(root);
            if (handler != null)
                handle(handler, path, req);
            else
                req.sendNotFound();
        }
    }

    private boolean auth(Request request) {
        var user = tokens.retrieve(request.getToken());
        if (user == null)
            return false;

        request.setOption("username", user.username());
        request.setOption("email", user.email());

        return true;
    }

    private void handle(Handler handler, String[] path, Request req) {
        req.dispatch();
        executor.execute(() -> {
            try {
                if (handler.doAuth()) {
                    if (!auth(req)) {
                        req.sendNoToken();
                        return;
                    }
                }
                handler.handle(path, req);
            } catch (Throwable ex) {
                try {
                    req.sendErr("problem on request: " + ex.getMessage());
                    log.warn("problem on {}: {}", req, Exceptions.cleanMessage(ex));
                }
                catch (Exception other) {
                    log.error("problem on request: {}", req, ex);
                }
            }
        });
    }
}
