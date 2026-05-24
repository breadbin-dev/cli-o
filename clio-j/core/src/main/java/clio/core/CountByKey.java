package clio.core;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public class CountByKey<T> {

    private final Map<T, Integer> counter = new HashMap<>();

    public int get(T key) {
        var c = counter.get(key);
        return c == null ? 0 : c;
    }

    public int increment(T key) {
        var c = get(key) + 1;
        counter.put(key, c);
        return c;
    }

    public int remove(T key) {
        var c = counter.remove(key);
        return c == null ? 0 : c;
    }

    public void removeAll(Iterable<T> keys) {
        for (var k : keys)
            remove(k);
    }

    public Set<T> keys() {
        return counter.keySet();
    }

    public void clear() {
        counter.clear();
    }
}
