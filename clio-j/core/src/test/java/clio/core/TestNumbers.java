package clio.core;

import clio.core.Numbers;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

public class TestNumbers {
    @Test
    public void testDeviation() {
        assertEquals(1.0, Numbers.deviation(0, 10), 0.001);
        assertEquals(1.0, Numbers.deviation(10, 0), 0.001);
        assertEquals(0.0, Numbers.deviation(10, 10), 0.001);
        assertEquals(0.4, Numbers.deviation(10, 6), 0.001);
        assertEquals(0.4, Numbers.deviation(6, 10), 0.001);
        assertEquals(1.4, Numbers.deviation(-10, 4), 0.001);
        assertEquals(1.4, Numbers.deviation(-4, 10), 0.001);
    }

    @Test
    public void testFloorToZero() {
        assertEquals(10, Numbers.floorToZero(10.1));
        assertEquals(12, Numbers.floorToZero(12.9));
        assertEquals(-10, Numbers.floorToZero(-10.1));
        assertEquals(-12, Numbers.floorToZero(-12.9));

        assertEquals(11100, Numbers.floorToZero(11111, 100));
        assertEquals(11200, Numbers.floorToZero(11299, 100));
        assertEquals(-11100, Numbers.floorToZero(-11111, 100));
        assertEquals(-11200, Numbers.floorToZero(-11299, 100));
    }
}
