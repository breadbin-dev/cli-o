package clio.core.kdb;

import com.kx.c;
import clio.core.tables.ColumnarTable;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import static clio.core.Strings.f;

public class KdbConnection {

    public static c.Dict toDict(Map<?, ?> obj) {
        var keys = new Object[obj.size()];
        var values = new Object[obj.size()];
        var i = 0;
        for (var e : obj.entrySet()) {
            keys[i] = e.getKey();
            values[i] = e.getValue();
            i++;
        }
        return new c.Dict(keys, values);
    }

    public static Map<String, ?> toMap(c.Dict dict) {
        var x = (String[])dict.x;
        var y = (Object[])dict.y;
        var result = new HashMap<String, Object>();

        for (var i = 0; i < x.length; i++) {
            result.put(x[i], y[i]);
        }

        return result;
    }

    public static ColumnarTable toTable(Object obj) {
        var flip = (c.Flip)obj;
        return new ColumnarTable(flip.x, flip.y);
    }

    public static Object encode(Object obj) {
        if (obj instanceof Map)
            return toDict((Map<?, ?>) obj);
        return obj;
    }

    private final String host;
    private final int port;
    private final String userpwd;

    private c _connection = null;

    public KdbConnection(String url, String user, String pwd) {
        var urls = url.split(":");
        this.host = urls[0];
        this.port = Integer.parseInt(urls[1]);
        this.userpwd = user + ":" + pwd;
    }

    public Object query(String query) {
        return this.query(query, null, null);
    }

    public Object query(String query, Object arg) {
        return this.query(query, arg, null);
    }

    private void reconnect() {
        try {
            _connection = new c(host, port, userpwd);
        }
        catch (Exception ex) {
            throw new KdbConnectionException(f("problem connecting [{}:{}]", host, port), ex);
        }
    }

    public Object retry(Object query) {

        if (_connection == null)
            reconnect();

        try {
            return _connection.k(query);
        } catch (IOException ioex) {
            reconnect();
            try {
                return _connection.k(query);
            } catch (Exception ex) {
                return new KdbQueryException(ex.getMessage(), ex);
            }
        } catch (c.KException kex) {
            throw new KdbQueryException(kex.getMessage(), kex);
        }
    }

    public <T> T query(String query, Object arg1, Object arg2) {
        try {
            Object arg;
            if (arg2 != null)
                arg = new Object[]{query.toCharArray(), encode(arg1), encode(arg2)};
            else if (arg1 != null)
                arg = new Object[]{query.toCharArray(), encode(arg1)};
            else
                arg = query.toCharArray();

            var result = retry(arg);
            if (result instanceof c.Dict)
                return (T) toMap((c.Dict) result);
            else if (result instanceof c.Flip)
                return (T) toTable(result);
            else
                return (T) result;
        } catch (KdbConnectionException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new KdbQueryException(f("problem on query: {}", query), ex);
        }
    }
}
