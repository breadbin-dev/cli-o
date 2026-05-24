package clio.core;

import java.util.HashMap;
import java.util.Map;

public class TypedHashMap<K> extends HashMap<K, Object> {

    public TypedHashMap() {}

    public TypedHashMap(Map<K, ?> map) {
        super(map);
    }

    public <T> T getT(K key) {
        return (T) get(key);
    }

    public <T> T getT(K key, T dflt) {
        var value = getT(key);
        return value == null ? dflt : (T)value;
    }

    public <T> T getT(K key, T dflt, Class<T> clz) {
        var value = getT(key);
        if (value instanceof String)
            return Strings.parse((String)value, clz);
        return value == null ? dflt : (T)value;
    }

    public <T> T ensureT(K key) {
        return (T)Collections.ensure(this, key);
    }
}
