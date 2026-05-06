package clio.router;


import clio.core.Strings;
import clio.router.entitlements.Entitlements;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

public class QueueHandler implements Handler {

    private static final Logger log = LogManager.getLogger(QueueHandler.class);

    private final ConcurrentHashMap<String, Queue> queues = new ConcurrentHashMap<>();

    private final ConcurrentHashMap<String, String> functionToQueue = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, String> descriptions = new ConcurrentHashMap<>();

    private final Supplier<String> callers = Strings.uniqueCounter();
    private final Entitlements entitlements;

    public QueueHandler(Entitlements entitlements) {
        this.entitlements = entitlements;
    }

    public List<String> roots() {
        return List.of("subscribe", "call", "respond", "describe", "publish");
    }

    private Socket newSocket(Queue socket, String q) {
        var name = socket.nextID();
        return new Socket(name, () -> socket.socketDrop(name), d -> setDescription(q, d));
    }

    private void setDescription(String queue, String description) {
        var descs = (Map<String, String>)Strings.readJson(description, Map.class);
        this.descriptions.putAll(descs);
        for (var k : descs.keySet()) {
            functionToQueue.put(k, queue);
        }
    }

    private Queue ensureQueue(String name) {
        return queues.computeIfAbsent(name, n -> new Queue(n, entitlements));
    }

    @Override
    public void handle(String[] path, Request req) {
        if (path.length < 1)
            throw new RuntimeException("Action not provided");

        var action = path[0];
        if ("describe".equals(action) && path.length == 1) {
            var desc = new HashMap<>(descriptions);
            req.sendJson(Strings.toJson(desc));
            log.debug("provided descriptions: {}", desc);
            return;
        }

        if (path.length < 2)
            throw new RuntimeException("Function not provided");

        var q = path[1];
        if ("call".equals(action) || "respond".equals(action) || "publish".equals(action)) {
            q = functionToQueue.containsKey(q) ? functionToQueue.get(q) : q.split("\\.")[0];
        }

        var queue = "subscribe".equals(action) ? ensureQueue(q) : queues.get(q);
        if (queue == null)
            throw new RuntimeException("Queue not found [" + q + "]");

        switch (action) {
            case "subscribe" -> queue.subscribe(newSocket(queue, q).handle(req));
            case "call" -> queue.call(req, callers.get());
            case "respond" -> queue.respond(req);
            case "publish" -> queue.publish(req);
            default -> throw new RuntimeException("Unknown action [" + action + "]: " + req);
        }
    }
}
