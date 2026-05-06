package clio.core;

import java.util.*;
import java.util.function.BiFunction;
import java.util.function.Function;

public class NestedMap<K, V> {
    private final Map<K, Object> map = new HashMap<>();

    public void put(K key, V value) {
        map.put(key, (Object)value);
    }

    @SafeVarargs
    public final void put(V value, K... keys) {
        put(keys, 0, value);
    }

    @SafeVarargs
    public final void putAll(NestedMap<K, V> values, K... keys) {
        combineAll(values, (current, next) -> next, keys);
    }

    @SafeVarargs
    public final void combineAll(NestedMap<K, V> values, BiFunction<V, V, V> combinator, K... keys) {
        if (keys.length == 0) {
            for (var e : values.map.entrySet()) {
                var k = e.getKey();
                var v = e.getValue();
                if (v instanceof NestedMap) {
                    ensureChild(k).combineAll((NestedMap<K, V>)v, combinator);
                } else {
                    if (map.containsKey(k))
                        map.put(k, combinator.apply((V)map.get(k), (V)v));
                    else
                        map.put(k, v);
                }
            }
        } else {
            ensureChild(keys).combineAll(values, combinator);
        }
    }

    protected void put(K[] keys, int i, V value) {
        var last = keys.length - 1;
        if (i == last)
            put(keys[last], value);
        else
            ensureChild(keys[i]).put(keys, i + 1, value);
    }

    public V get(K key) {
        return (V)map.get(key);
    }

    @SafeVarargs
    public final V get(K... keys) {
        return (V)getOrEnsure(0, false, false, keys);
    }

    @SafeVarargs
    public final V remove(K... keys) {
        return (V)getOrEnsure(0, false, true, keys);
    }

    @SafeVarargs
    public final V computeIfAbsent(Function<? super K, ? extends V> mappingFunction, K... keys) {
        return computeIfAbsent(keys, 0, mappingFunction);
    }

    protected V computeIfAbsent(K[] keys, int i, Function<? super K, ? extends V> mappingFunction) {
        var last = keys.length - 1;
        if (i == last)
            return (V)map.computeIfAbsent(keys[last], mappingFunction);
        else
            return ensureChild(keys[i]).computeIfAbsent(keys, i + 1, mappingFunction);
    }

    @SafeVarargs
    public final NestedMap<K, V> ensureChild(K... keys) {
        return (NestedMap<K, V>)getOrEnsure(0, true, false, keys);
    }

    @SafeVarargs
    public final NestedMap<K, V> removeChild(K... keys) {
        return (NestedMap<K, V>)getOrEnsure(0, false, true, keys);
    }

    @SafeVarargs
    public final NestedMap<K, V> getChild(K... keys) {
        return (NestedMap<K, V>)getOrEnsure(0, false, false, keys);
    }

    @SafeVarargs
    protected final Object getOrEnsure(int i, boolean ensure, boolean remove, K... keys) {
        var isLast = i == keys.length - 1;
        var key = keys[i];

        var obj = isLast && remove ? map.remove(key) : map.get(key);
        if (ensure && obj == null)
            map.put(key, obj = new NestedMap<K, V>());

        if (isLast || obj == null)
            return obj;
        else {
            var child = ((NestedMap<K,V>)obj);
            var result = child.getOrEnsure(i + 1, ensure, remove, keys);
            if (remove && child.isEmpty())
                map.remove(key);
            return result;
        }
    }

    public Set<Map.Entry<K, NestedMap<K, V>>> children() {
        return (Set<Map.Entry<K, NestedMap<K, V>>>)(Object)map.entrySet();
    }

    public Set<Map.Entry<K, V>> entries() {
        return (Set<Map.Entry<K, V>>)(Object)map.entrySet();
    }

    public Collection<V> leaves() {
        var leaves = new ArrayList<V>();
        collectLeaves(leaves);
        return leaves;
    }

    protected void collectLeaves(Collection<V> leaves) {
        for (var v : map.values()) {
            if (v instanceof NestedMap)
                ((NestedMap<?, V>) v).collectLeaves(leaves);
            else
                leaves.add((V)v);
        }
    }

    public boolean isEmpty() {
        return map.isEmpty();
    }

    public int size() {
        var i = 0;
        for (var e : map.values()) {
            if (e instanceof NestedMap)
                i += ((NestedMap<?, ?>)e).size();
            else
                ++i;
        }
        return i;
    }

    public int branchSize() {
        return map.size();
    }

    public void clear() {
        map.clear();
    }
}
