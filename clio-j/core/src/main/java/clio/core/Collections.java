package clio.core;

import java.util.*;
import java.util.function.BiFunction;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.stream.Collectors;

import static clio.core.Strings.f;

public class Collections {

    public static <T1,T2> List<T2> map(T1[] input, Function<T1,T2> mapper) {
        return Arrays.stream(input).map(mapper).toList();
    }

    public static <T1,T2> List<T2> map(Collection<T1> input, Function<T1,T2> mapper) {
        return input.stream().map(mapper).toList();
    }

    public static <T1,T2> T2 mapUnique(Collection<T1> input, Function<T1,T2> mapper) {
        var results = new HashSet<>(map(input, mapper));
        return single(results);
    }

    public static <K, T1, T2> Map<K, T2> mapReduce(Collection<T1> input, Function<T1,T2> mapper, BiFunction<T1, T2, K> key) {
        var result = new HashMap<K, T2>();
        for (var i : input) {
            var r = mapper.apply(i);
            result.put(key.apply(i, r), r);
        }
        return result;
    }

    public static <K, T> Map<K, List<T>> collectByKey(Iterable<T> input, Function<T, K> key) {
        var result = new HashMap<K, List<T>>();
        for (var i : input)
            result.computeIfAbsent(key.apply(i), x -> new ArrayList<>()).add(i);
        return result;
    }

    public static <K, T> Map<K, T> collectByUniqueKey(Collection<T> input, Function<T, K> key) {
        return input.stream().collect(Collectors.toMap(key, Function.identity()));
    }

    public static <K, V1, V2> Map<K, V2> map(Map<K, V1> input, BiFunction<K, V1, V2> mapper) {
        return input.entrySet().stream().collect(Collectors.toMap(Map.Entry::getKey, e -> mapper.apply(e.getKey(), e.getValue())));
    }

    public static <K1, V1, K2, V2> Map<K2, V2> map(Map<K1, V1> input, BiFunction<K1, V1, K2> keyMapper, BiFunction<K1, V1, V2> valueMapper) {
        return input.entrySet().stream().collect(Collectors.toMap(e -> keyMapper.apply(e.getKey(), e.getValue()), e -> valueMapper.apply(e.getKey(), e.getValue())));
    }

    public static <K, V> V ensure(Map<K, V> map, K key) {
        return ensure(map, key, false);
    }

    public static Map<String, String> getChildProperties(Map<String, String> properties, String prefix) {
        var result = new HashMap<String, String>();
        for (var key : properties.keySet()) {
            if (key.startsWith(prefix))
                result.put(key.substring(prefix.length()), properties.get(key));
        }
        return result;
    }

    public static <K, V> V ensure(Map<K, V> map, K key, boolean remove) {
        return ensure(map, key, remove, null);
    }

    public static <K, V> V ensure(Map<K, V> map, K key, boolean remove, String message) {
        var r = remove ? map.remove(key) : map.get(key);
        if (r == null)
            throw new RuntimeException(Strings.hasValue(message) ? message : ("[" + key + "] not found"));
        return r;
    }

    public static <T> Collection<T> reverse(Collection<T> collection) {
        var copy = new ArrayList<>(collection);
        java.util.Collections.reverse(copy);
        return copy;
    }

    public static <T> List<T> emptyList() {
        return java.util.Collections.emptyList();
    }

    public static <T> Set<T> emptySet() {
        return java.util.Collections.emptySet();
    }

    public static <K, V> Map<K, V> emptyMap() {
        return java.util.Collections.emptyMap();
    }

    public static <T> List<T> collect(Iterable<T> i) {
        var result = new ArrayList<T>();
        for (var t : i)
            result.add(t);
        return result;
    }

    @SafeVarargs
    public static <T> List<T> collect(Collection<T>... is) {
        var result = new ArrayList<T>();
        for (var i : is)
            result.addAll(i);
        return result;
    }

    public static <K, T> List<T> reduce(Collection<Map<K, T>> listOfMaps) {
        var result = new ArrayList<T>();
        for (var i : listOfMaps)
            result.addAll(i.values());
        return result;
    }


    public static <T> Iterable<T> repeat(T item, int n) {
        return () -> new Iterator<>() {
            int i = 0;
            @Override
            public boolean hasNext() {
                return i < n;
            }

            @Override
            public T next() {
                i += 1;
                return item;
            }
        };
    }

    public static <T> List<T> filter(Collection<T> items, Predicate<T> filter) {
        return items.stream().filter(filter).toList();
    }

    public static <K, V> Map<K, V> filter(Map<K, V> items, Predicate<Map.Entry<K, V>> filter) {
        return items.entrySet().stream().filter(filter).collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    // automatically remove items as you consume them
    public static <T> Iterable<T> take(Iterable<T> items) {
        var i = items.iterator();
        return () -> new Iterator<>() {
            @Override
            public boolean hasNext() {
                return i.hasNext();
            }

            @Override
            public T next() {
                var item = i.next();
                i.remove();
                return item;
            }
        };
    }

    @SafeVarargs
    public static <T> T nullOrSame(T... items) {
        T result = null;
        for (var item : items) {
            if (item != null) {
                if (result == null)
                    result = item;
                else if (!result.equals(item))
                    throw new RuntimeException(item + "!=" + result);
            }
        }
        return result;
    }

    public static <K, V> void putUnique(Map<K, V> map, K key, V value) {
        map.compute(key, (k, v) -> {
            if (v == null || v.equals(value))
                return value;
            throw new RuntimeException(f("{}->[{},{}] should be unique", key, value, v));
        });
    }

    @SuppressWarnings("unchecked")
    public static <T extends Comparable<?>> T safeMin(T a, T b) {
        if (a == null)
            return b;
        if (b == null)
            return a;
        return ((Comparable<T>)a).compareTo(b) > 0 ? b : a;
    }

    @SuppressWarnings("unchecked")
    public static <T extends Comparable<?>> T safeMax(T a, T b) {
        if (a == null)
            return b;
        if (b == null)
            return a;
        return ((Comparable<T>)a).compareTo(b) > 0 ? a : b;
    }

    public static <T> T single(Collection<T> items) {
        return single(items, null);
    }

    public static <T> T single(Collection<T> items, String message) {
        if (items.size() != 1)
            throw new RuntimeException(Strings.hasValue(message) ? message : f("Unexpectedly {} items", items.size()));
        return items.iterator().next();
    }

    public static <T> T singleOrNull(Collection<T> items) {
        if (items.size() != 1)
            return null;
        return items.iterator().next();
    }
}
