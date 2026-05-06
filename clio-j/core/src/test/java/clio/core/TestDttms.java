package clio.core;

import clio.core.Dttms;
import org.junit.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;

import static org.junit.Assert.assertEquals;

public class TestDttms {

    private void checkFormat(LocalDateTime dttm, int len) {
        var str = Dttms.formatDttm(dttm);
        assertEquals(len, str.length());
        assertEquals(dttm, Dttms.parseDttm(str));
    }

    @Test
    public void testFormatting() {
        checkFormat(LocalDateTime.of(2022, 6, 3, 10, 15, 30, 1), 24);
        checkFormat(LocalDateTime.of(2022, 6, 3, 10, 15, 30, 1000), 21);
        checkFormat(LocalDateTime.of(2022, 6, 3, 10, 15, 30, 1000000), 18);
        checkFormat(LocalDateTime.of(2022, 6, 3, 10, 15, 30), 15);
        checkFormat(LocalDateTime.of(2022, 6, 3, 10, 15), 13);
        checkFormat(LocalDateTime.of(2022, 6, 3, 10, 0), 11);
    }

    @Test
    public void testEpochNanos() {
        var early = LocalDateTime.of(1970, 1, 1, 0, 0, 0, 5);
        assertEquals(early, Dttms.fromEpochNanos(Dttms.toEpochNanos(early)));
        assertEquals(5, Dttms.toEpochNanos(early));

        var late = LocalDateTime.of(2260, 1, 1, 0, 0, 0, 5);
        assertEquals(late, Dttms.fromEpochNanos(Dttms.toEpochNanos(late)));

        var now = LocalDateTime.now();
        assertEquals(now, Dttms.fromEpochNanos(Dttms.toEpochNanos(now)));
    }

    @Test
    public void testShortCodes() {
        var now = LocalDateTime.now();
        assertEquals(now.plusMinutes(5), Dttms.parseDttm("now+5m", now));
        assertEquals(now.minusHours(2), Dttms.parseDttm("now-2h", now));

        assertEquals(Dttms.eod(now).plusMinutes(5), Dttms.parseDttm("eod+5m", now));
        assertEquals(Dttms.sod(now).minusSeconds(25), Dttms.parseDttm("sod-25s", now));

        assertEquals(LocalDate.now().atTime(LocalTime.of(10, 0)), Dttms.parseDttm("today+10h", now));
        assertEquals(LocalDate.now().atTime(LocalTime.of(10, 0)), Dttms.parseDttm("T+10h", now));
        assertEquals(LocalDate.now().minusDays(1).atTime(LocalTime.of(10, 30)), Dttms.parseDttm("yd+10:30", now));
        assertEquals(LocalDate.now().atTime(LocalTime.of(10, 0)), Dttms.parseDttm("T+10am", now));
        assertEquals(LocalDate.now().atTime(LocalTime.of(10, 15)), Dttms.parseDttm("T+10:15", now));
        assertEquals(LocalDate.now().atTime(LocalTime.of(10, 15, 4)), Dttms.parseDttm("T+10:15:04am", now));
        assertEquals(LocalDate.now().atTime(LocalTime.of(14, 30)), Dttms.parseDttm("T+2:30pm", now));
    }

    @Test
    public void testParseZoned() {
        assertEquals(Dttms.parseDttm("20250407_1630"), Dttms.parseOffsetDttm("2025-04-07T12:30:00.000-04:00"));
    }

    @Test
    public void testUserZone() {
        var dttm = Dttms.parseDttm("T+08:00@America/New_York", LocalDateTime.of(2023, 10, 1, 12, 0));
        assertEquals(Dttms.parseDttm("20231001_12"), dttm);
    }
}
