package clio.core;

import clio.core.Cron;
import clio.core.Dttms;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

public class TestCron {

    @Test
    public void testSimpleCron() {
        var schedule = Cron.of("0 * * * Mon-Fri");

        assertEquals("every hour every day between Monday and Friday UTC", schedule.desc());

        assertEquals(Dttms.parseDttm("20240201_23"), schedule.next(Dttms.parseDttm("20240201_22")));
        assertEquals(Dttms.parseDttm("20240201_23"), schedule.next(Dttms.parseDttm("20240201_2230")));

        assertEquals(Dttms.parseDttm("20240205_00"), schedule.next(Dttms.parseDttm("20240203_2230")));
    }

    @Test
    public void testZonedCron() {
        var schedule = Cron.of("0 15 * * Mon-Fri @America/New_York");

        assertEquals("at 15:00 every day between Monday and Friday America/New_York", schedule.desc());

        assertEquals(Dttms.parseDttm("20240201_20"), schedule.next(Dttms.parseDttm("20240201_05")));
        assertEquals(Dttms.parseDttm("20240205_20"), schedule.next(Dttms.parseDttm("20240203_21")));
    }
}
