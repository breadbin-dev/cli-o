package clio.core;

import clio.core.Collections;
import org.junit.Test;

import java.util.HashMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

public class TestCollections {

    @Test
    public void testPutUnique() {
        var map = new HashMap<String, String>();
        Collections.putUnique(map, "a", "x");
        Collections.putUnique(map, "b", "y");
        Collections.putUnique(map, "a", "x");
        assertEquals(2, map.size());
        assertEquals(map.get("a"), "x");
        assertEquals(map.get("b"), "y");

        assertThrows(Exception.class, () -> Collections.putUnique(map, "a", "z"));
    }
}
