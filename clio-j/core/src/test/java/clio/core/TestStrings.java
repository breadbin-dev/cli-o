package clio.core;

import clio.core.Strings;
import clio.core.TempFile;
import org.junit.Test;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

public class TestStrings {
    @Test
    public void testStringF() {
        assertEquals("a, 4, 3.33", Strings.f("{}, {}, {}", "a", 4, Strings.fs("%.2f", 10.0/3)));
    }

    public record MockRecord(String a, int b, double c) {}

    @Test
    public void testJsonReadWrite() {
        try (var tf = new TempFile()) {
            var a = new MockRecord("a", 4, 3.33);
            Strings.writeJson(tf.file(), a);
            var b = Strings.readJson(tf.file(), MockRecord.class);
            assertEquals(a, b);
        }
    }

    @Test
    public void testJsonNaN() {
        @SuppressWarnings("unchecked")
        Map<String, ?> map = Strings.readJson("{\"a_nan\": NaN}", Map.class);
        assert Double.isNaN((Double)map.get("a_nan"));
    }

    @Test
    public void testCamelToSnake() {
        assertEquals("bob_the_builder", Strings.camelToSnake("bobTheBuilder"));
    }

    @Test
    public void testSplitBySpace() {
        assertEquals(List.of("a", "string", "with", "other strings", "in", "it"), Strings.splitBySpaces("a string with \"other strings\" in it"));
    }

    @Test
    public void testTimeCode() {
        var now = LocalDateTime.now();
        assertEquals(7, Strings.timeCode(now, 7).length());
        assertEquals(Strings.timeCode(now, 5), Strings.timeCode(now, 5));
        assertNotEquals(Strings.timeCode(now, 5), Strings.timeCode(now.plusSeconds(5), 5));
    }

    @Test
    public void testRandom() {
        assertEquals(12, Strings.random(12).length());
        assertNotEquals(Strings.random(12), Strings.random(12));
    }

    @Test
    public void testCounter() {
        var counter = Strings.uniqueCounter();
        assertNotEquals(counter.get(), counter.get());
    }

    @Test
    public void testSplitWithQuotes() {
        var split = Strings.splitWithQuotes("hello \"quoted text\" and -unquoted 5.0 --text");
        assertArrayEquals(new String[]{"hello", "quoted text", "and", "-unquoted", "5.0", "--text"}, split);
    }


    @Test
    public void testVariableReplacement() {
        var result = Strings.replaceVariables("Hello, ${name}! Today is ${day}.", varName -> switch (varName) {
            case "name" -> "Alice";
            case "day" -> "Monday";
            default -> null;
        });
        assertEquals("Hello, Alice! Today is Monday.", result);
    }

    @Test
    public void testStripDigitSuffix() {
        assertEquals("HI", Strings.stripDigitSuffix("HI"));
        assertEquals("HI", Strings.stripDigitSuffix("HI1"));
        assertEquals("HI", Strings.stripDigitSuffix("HI123"));
        assertEquals("", Strings.stripDigitSuffix("123"));
        assertEquals("", Strings.stripDigitSuffix(""));
    }

    @Test
    public void testRSplit() {
        assertArrayEquals(new String[]{"a,b,c", "d", "e"}, Strings.rsplit("a,b,c,d,e", ",", 3));
        assertArrayEquals(new String[]{"a,b,c,d", "e"}, Strings.rsplit("a,b,c,d,e", ",", 2));
        assertArrayEquals(new String[]{"a", "b", "c"}, Strings.rsplit("a,b,c", ",", 3));
    }
}
