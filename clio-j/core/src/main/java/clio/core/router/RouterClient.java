package clio.core.router;

import clio.core.Param;
import clio.core.Strings;
import clio.core.rest.RestClient;

import java.util.HashMap;
import java.util.Map;

public class RouterClient {

    private final RestClient rest;

    public RouterClient(String url, String token) {
        this.rest = new RestClient(url, new Param("Authorization", "Token " + token));
    }

    public Map<String, ?> call(String function) {
        var i = function.indexOf(" ");
        return i == -1 ? call(function, "") : call(function.substring(0, i), function.substring(i + 1));
    }

    public Map<String, ?> call(String function, String args) {
        return call(function, args, "text");
    }

    public Map<String, ?> call(String function, Map<String, ?> args) {
        return call(function, Strings.toJson(args), "json");
    }

    public Map<String, ?> call(String function, String args, String argsType) {
        var call = new HashMap<String, String>();
        call.put("function", function);
        call.put("args", args);
        call.put("args_type", argsType);
        var queue = function.split("\\.")[0];
        var result = (Map<String, ?>)rest.get("call/" + queue, Map.class, Strings.toJson(call));

        if ("err".equals(result.get("type")))
            throw new RuntimeException((String)result.get("result"));

        return result;
    }

    public String respond(String queue, String type, Object result, String callId) {
        var response = new HashMap<String, Object>();
        response.put("type", type);
        response.put("result", result);
        return rest.get("respond/" + queue, String.class, Strings.toJson(response), new Param("CallerID", callId));
    }

    public String publish(String function, String type, Map<String, ?> updates, int refreshMs, boolean full) {
        var publication = new HashMap<String, Object>();
        publication.put("function", function);
        publication.put("type", type);
        publication.put("result", updates);
        publication.put("refresh_period", refreshMs);
        if (full)
            publication.put("is_full", full);
        var queue = function.split("\\.")[0];
        return rest.get("publish/" + queue, String.class, Strings.toJson(publication));
    }

    public static void main(String[] commandLine) {
        var client = new RouterClient("http://localhost:4410", "api-lys2y1wjGcFDYcb");
        System.out.println(client.call("demo.cache"));
    }
}
