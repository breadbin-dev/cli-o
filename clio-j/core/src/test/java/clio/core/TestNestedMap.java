package clio.core;

import clio.core.NestedMap;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

public class TestNestedMap {

    @Test
    public void testNestedMap() {

        var map = new NestedMap<String, Integer>();

        map.put(1, "a", "b", "c");
        map.put(2, "a", "b", "d");

        assertEquals((Integer)1, map.get("a", "b", "c"));
        assertEquals((Integer)1, map.computeIfAbsent(x -> 2, "a", "b", "c"));
        assertEquals((Integer)3, map.computeIfAbsent(x -> 3, "x", "y", "z"));
        assertEquals(3, map.size());
        assertEquals(2, map.branchSize());

        assertEquals((Integer)3, map.remove("x", "y", "z"));
        assertEquals(2, map.size());
        assertEquals(1, map.branchSize());

        assertEquals((Integer)1, map.remove("a", "b", "c"));
        assertEquals(1, map.size());
        assertEquals(1, map.branchSize());

        assertEquals((Integer)2, map.remove("a", "b", "d"));
        assertEquals(0, map.size());
        assertEquals(0, map.branchSize());
    }

    @Test
    public void testBulkUpdate() {

        var map1 = new NestedMap<String, Integer>();
        map1.put(1, "a", "b", "c");
        map1.put(2, "a", "c", "d");

        var map2 = new NestedMap<String, Integer>();
        map2.put(3, "a", "b", "c");
        map2.put(4, "a", "c", "d");

        map2.putAll(map1.removeChild("a", "c"));

        assertEquals(1, map1.size());
        assertEquals(3, map2.size());
    }

}
