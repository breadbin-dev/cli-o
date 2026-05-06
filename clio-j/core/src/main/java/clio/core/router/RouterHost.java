package clio.core.router;

import clio.core.*;
import clio.core.ws.WebSocketClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static clio.core.Strings.f;

public class RouterHost implements Disposable {

    private static final Logger log = LoggerFactory.getLogger(RouterHost.class);

    record FunctionWrapper<TArgs>(String function, Subscription<Call<TArgs>> func, ArgParser<TArgs> args) {
        public void call(Call<TArgs> call) {
            try {
                func.accept(call.callId, call);
            } catch (UserException ex) {
                call.respondErr(f("[{}]: {}", function, Exceptions.msg(ex)));
            } catch (Throwable ex) {
                log.warn("Problem on call [{}]", function, ex);
                call.respondErr(f("Problem [{}]: {}", function, Exceptions.msg(ex)));
            }
        }

        public TArgs parseArgs(String args) {
            if (args == null || args.isEmpty())
                return (TArgs)Collections.emptyMap();

            if (this.args == null)
                throw new RuntimeException("unexpected args: " + args);

            return this.args.parse(args);
        }
    }

    public record Call<TArgs>(String queue, String function, TArgs args, String user, String callId, RouterClient client) {
        public void respond(String type, Object result) {
            client.respond(queue, type, result, callId);
        }

        public void respondErr(String msg) {
            respond("err", msg);
        }

        public void respondText(String result) {
            respond("text", result);
        }

        public void respondOK() {
            respond("text", "OK");
        }

        public <T> T ensureArg(String name) {
            return (T)Collections.ensure((Map<String, ?>)args, name);
        }

        public <T> T getArg(String name) {
            return (T)((Map<String, ?>)args).get(name);
        }

        public boolean hasArg(String name) {
            return ((Map<String, ?>)args).containsKey(name);
        }

        public <T> T getArg(String name, Class<T> clz) {
            String value = getArg(name);
            if (value == null) {
                return null;
            } else if (clz == String.class) {
                return clz.cast(value);
            } else if (clz == Double.class || clz == double.class) {
                return clz.cast(Double.parseDouble(value));
            } else if (clz == Long.class || clz == long.class) {
                return clz.cast(Long.parseLong(value));
            } else if (clz == TypedHashMap.class) {
                var map = (Map<String, Object>)Strings.readJson(value, Map.class);
                return clz.cast(new TypedHashMap<>(map));
            } else {
                throw new IllegalArgumentException("Unsupported type: " + clz.getName());
            }
        }

        public <T> T getArg(String name, Class<T> clz, T dflt) {
            var r = getArg(name, clz);
            return r == null ? dflt : r;
        }

        public <T extends Enum<T>> T getEnum(String name, Class<T> clz, T dflt) {
            var r = getArg(name, String.class);
            return r == null ? dflt : Enum.valueOf(clz, r);
        }
    }

    private final HashMap<String, FunctionWrapper> functions = new HashMap<>();
    private final HashMap<String, String> descriptions = new HashMap<>();

    private final String url;
    private final RouterClient client;
    private final String token;
    private final String queue;
    private final String functionRoot;
    private final String description;

    private volatile WebSocketClient socket;
    private volatile boolean connected = false;

    private final SubscriptionFuture<Boolean> connectedListener = new SubscriptionFuture<>();

    public RouterHost(String url, String token, String queue, String functionRoot, String description) {
        this.url = url.replace("http://", "ws://");
        this.client = new RouterClient(url, token);
        this.token = token;
        this.queue = queue;
        this.functionRoot = functionRoot;
        this.description = description;
    }

    public String queue() {
        return this.queue;
    }

    public RouterClient client() {
        return this.client;
    }

    public void onCall(String key, String value) {
        var msg = (Map<String, String>)Strings.readJson(value, Map.class);
        var function = msg.get("function");

        Call call = null;
        try {
            var fw = functions.get(function);
            if (fw == null)
                throw new RuntimeException("function not found: " + function);
            var args = fw.parseArgs(msg.get("args"));
            call = new Call(queue, function, args, msg.get("username"), msg.get("call_id"), client);
            fw.call(call);
        } catch (Throwable ex) {
            if (call == null)
                call = new Call(queue, function, null, msg.get("username"), msg.get("call_id"), client);
            call.respondErr(Exceptions.msg(ex));
        }
    }

    private String functionRoot() {
        return functionRoot == null ? queue : functionRoot;
    }

    public <TArgs> void add(String function, String desc, Subscription<Call<TArgs>> func, ArgParser<TArgs> parser) {
        var hidden = function.startsWith("_");
        function = f("{}.{}", functionRoot(), function);
        functions.put(function, new FunctionWrapper<TArgs>(function, func, parser));
        if (!hidden)
            descriptions.put(function, desc);
    }

    public void add(String function, String desc, Subscription<Call<Map<String, Object>>> func, CliArgParser.Option... options) {
        StringBuilder descBuilder = new StringBuilder(desc);
        for (var option : options) {
            if (!option.longOpt().startsWith("_"))
                descBuilder.append("\n").append(option);
        }
        desc = descBuilder.toString();
        add(function, desc, func, CliArgParser.of(options));
    }

    public Publisher publish(String function, String desc, String type, int refreshMs) {
        var hidden = function.startsWith("_");
        function = f("{}.{}", functionRoot(), function);
        if (!hidden)
            descriptions.put(function, desc);
        return new Publisher(client, function, type, refreshMs);
    }

    public TablePublisher publishTable(String function, String desc, int refreshMs) {
        var hidden = function.startsWith("_");
        function = f("{}.{}", functionRoot(), function);
        if (!hidden)
            descriptions.put(function, desc);
        return new TablePublisher(client, function, refreshMs);
    }

    public boolean isConnected() {
        return connected;
    }

    public void awaitConnected() {
        var connected = connectedListener.get(5, TimeUnit.SECONDS);
        if (connected == null || !connected)
            throw new RuntimeException("Failed to connect");
    }

    public String listen() {
        try {
            var handler = Subscription.withLog(this::onCall, log);
            var ws = new WebSocketClient(f("{}/{}/{}", this.url, "subscribe", queue), this.token, handler).subscribe();
            socket = ws.get(5, TimeUnit.SECONDS);

            var desc = new HashMap<String, String>();
            desc.put(queue, description);
            desc.putAll(descriptions);

            socket.send(Strings.toJson(desc));

            connected = true;
            connectedListener.onResult(true);

            return socket.awaitDispose().get();
        }
        finally {
            connected = false;
            connectedListener.onResult(false);
        }
    }

    public void close() {
        var socket = this.socket;
        if (socket != null)
            socket.close();
    }

    public void listenAsync() {
        listenAsync(false);
    }

    public void listenAsync(boolean awaitConnected) {
        var hook = new ShutdownHook();
        Executors.newSingleThreadExecutor(new NamedThreads(queue)).execute(() ->
        {
            while (hook.running()) {
                try {
                    var disposed = listen();
                    log.warn("[{}]: {}", queue, disposed);
                } catch (Exception e) {
                    log.warn("[{}]: {}", queue, e.getMessage());
                }
                Executor.safeSleep(5000);
            }
        });

        if (awaitConnected)
            this.awaitConnected();
    }

    public static void main(String... args) {
        var host = new RouterHost("http://localhost:4410", "api-oV5afiUs6q0k2oI", "demo2", null,  "demo commands");

        host.add("hello", "respond to hello", Subscription.withLog((func, call) -> call.respondText("how do you do"), log));
        var cache = host.publishTable("cache", "demo of broker caching", 1000);
        cache.addColumns("sym", "item");

        host.listenAsync(true);

        var rows = new HashMap<String, Object>();
        rows.put("a", new LinkedHashMap<String, Object>(){{
            put("sym", "a");
            put("item", 1.0);
        }});
        rows.put("b", new LinkedHashMap<String, Object>(){{
            put("sym", "b");
            put("item", 0.0);
        }});

        cache.publish(rows);

        Executors.newSingleThreadExecutor(new NamedThreads("demo2")).submit(() -> {
            rows.clear();
            var count = 0.0;
            while (true) {
                final var i = count += 1.0;
                rows.put("b", Map.of(
                    "sym", "b",
                    "item", i
                ));
                cache.publish(rows);
                Executor.safeSleep(5000);
            }
        });

        new Application().run(true);
        host.close();
    }
}


