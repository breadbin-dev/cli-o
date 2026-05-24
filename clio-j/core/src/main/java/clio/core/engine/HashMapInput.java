package clio.core.engine;

import java.util.HashMap;
import java.util.Map;

public class HashMapInput<K, V> implements MapInput<K, V, Map<K, V>> {

    private final HashMap<K, V> in = new HashMap<>();
    private final HashMap<K, V> out = new HashMap<>();

    @Override
    public void in(long seq, K key, V value) {
        this.in.put(key, value);
    }

    @Override
    public void inAll(long seq, Map<K, V> in) {
        this.in.putAll(in);
    }

    @Override
    public Map<K, V> tick() {
        out.putAll(in);
        in.clear();
        return out;
    }
}
