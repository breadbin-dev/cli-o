package clio.router;

import clio.core.Collections;
import clio.core.Dttms;
import clio.core.SetOfSets;
import clio.core.Strings;
import clio.core.router.VarArgParser;
import clio.router.entitlements.Entitlements;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

public class Queue {

    record Call (String callID, String socket, Request request, String content){}

    private static final Logger log = LogManager.getLogger(Queue.class.getName());

    private final Map<String, Socket> listeners = new HashMap<>();
    private final Map<String, Call> callsByID = new HashMap<>();
    private final SetOfSets<String, String> callsBySocket = new SetOfSets<>();

    private final ConcurrentHashMap<String, Publication> publications = new ConcurrentHashMap<>();

    private final Supplier<String> ids;
    private final Entitlements entitlements;
    private final String name;

    private int robin;

    public Queue(String name, Entitlements entitlements) {
        this.name = name;
        this.ids = Strings.counter(name);
        this.entitlements = entitlements;
    }

    public void subscribe(Socket socket) {
        synchronized (this) {
            listeners.put(socket.name(), socket);
        }
        log.info("[{}] subscribed {}", name, socket);
    }

    public String nextID() {
        return ids.get();
    }

    private Socket next() {
        var open = new ArrayList<Socket>();
        var i = listeners.values().iterator();

        while (i.hasNext()) {
            var s = i.next();
            if (s.isOpen())
                open.add(s);
            else if(s.isClosed())
                i.remove();
        }

        if (open.isEmpty())
            throw new RuntimeException("Nobody listening");

        return open.get(robin = ++robin % open.size());
    }

    @SuppressWarnings("unchecked")
    private Map<String, ?> preprocessCall(String content, String user, String callID) {
        var result = Strings.readJson(content, Map.class);
        entitlements.check(user, (String)result.get("function"));
        result.put("username", user);
        result.put("call_id", callID);
        return result;
    }

    public void call(Request req, String callID) {
        Socket socket;
        var content = preprocessCall(req.text(), req.username(), callID);
        var function = (String)content.get("function");
        var publication = publications.get(function);
        if (publication != null) {
            var since = (String)content.get("since");

            var argsStr = (String)content.get("args");
            Map<String, Object> args = null;
            if (Strings.hasValue(argsStr))
                args = new VarArgParser().parse(argsStr);

            var results = publication.results(since == null ? null : Dttms.parseDttm(since), args);
            req.sendJson(Strings.toJson(results));
            log.debug("[{}:{}] pub response {} - {}", name, callID, function, req);
        }
        else {
            var contentStr = Strings.toJson(content);
            synchronized (this) {
                socket = next();
                callsByID.put(callID, new Call(callID, socket.name(), req, contentStr));
                callsBySocket.put(socket.name(), callID);
            }
            log.debug("[{}:{}] call {} -> {}", name, callID, req, socket);
            socket.send(contentStr);
        }
    }

    @SuppressWarnings("unchecked")
    public void publish(Request req) {
        var result = Strings.readJson(req.text(), Map.class);
        var publication = publications.computeIfAbsent(
                (String)result.get("function"),
                k -> new Publication((String)result.get("type"), (int)result.get("refresh_period"))
        );
        publication.update((Map<String, Object>)result.get("result"), (Boolean)result.get("is_full"));
        req.sendOK();
    }

    public void respond(Request resp) {
        var callID = resp.<String>ensureOption("CallerID");
        Call call;
        synchronized (this) {
            call = Collections.ensure(callsByID, callID, true);
            callsBySocket.remove(call.socket, callID);
        }
        log.debug("[{}:{}] response {} -> {}", name, callID, resp, call.request);
        call.request.sendText(resp.text());
        resp.sendOK();
    }

    public void socketDrop(String socket) {
        var dropped = new ArrayList<Call>();
        synchronized (this) {
            var s = listeners.remove(socket);
            if (s != null) {
                log.info("[{}] dropped socket {}", name, s);

                for (var callID : callsBySocket.remove(socket)) {
                    var call = callsByID.remove(callID);
                    if (call != null)
                        dropped.add(call);
                }
            }
        }

        for (var call : dropped) {
            log.warn("[{}:{}] dropped [{}] -> {}", name, call.callID, socket, call.request);
            call.request.sendErr("Dropped");
        }
    }
}
