package clio.core;

import clio.core.CronSession;
import clio.core.Dttms;
import org.junit.Test;

import static org.junit.Assert.*;

public class TestCronSession {

    @Test
    public void testSession() {
        var session = CronSession.of("50 17 * * Sun @America/New_York", "05 17 * * Fri @America/New_York");

        assertTrue(session.isOpen(Dttms.parseDttm("20250829_2055")));
        assertFalse(session.isOpen(Dttms.parseDttm("20250829_2106")));

        assertFalse(session.isOpen(Dttms.parseDttm("20250831_2140")));
        assertTrue(session.isOpen(Dttms.parseDttm("20250831_2155")));
    }
}
