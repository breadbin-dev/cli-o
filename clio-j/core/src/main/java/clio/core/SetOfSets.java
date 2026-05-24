package clio.core;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class SetOfSets<K, V> {

    private final Map<K, Set<V>> sets = new HashMap<>();

    public boolean put(K key, V value) {
        return sets.computeIfAbsent(key, k -> new HashSet<>()).add(value);
    }

    public boolean remove(K key, V value) {
        var set = sets.get(key);
        if (set != null) {
            var result = set.remove(value);
            if (set.isEmpty())
                sets.remove(key);
            return result;
        }
        return false;
    }

    public Set<V> remove(K key) {
        var result = sets.remove(key);
        return result == null ? java.util.Collections.emptySet() : result;
    }
}
