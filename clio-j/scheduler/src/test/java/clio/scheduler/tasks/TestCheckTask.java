package clio.scheduler.tasks;

import clio.core.Collections;
import clio.core.router.RouterClient;
import clio.core.tables.ArrayTable;
import clio.scheduler.tasks.CheckTask;
import org.junit.Test;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

public class TestCheckTask {

    class MockRouterClient extends RouterClient {

        Map<String, String> nextResponse = null;
        Exception nextException = null;
        Map<String, ?> lastBulk = null;

        public MockRouterClient() {
            super("", null);
        }

        @Override
        public Map<String, String> call(String function) {
            if (nextException != null) {
                var ex = nextException;
                nextException = null;
                throw new RuntimeException(ex);
            }

            var nr = nextResponse;
            nextResponse = null;
            return nr;
        }

        public Map<String, String> call(String function, Map<String, ?> args) {
            assertEquals("tickets.bulk", function);
            lastBulk = args;
            return null;
        }

        Map<String, ?> take() {
            var bulk = lastBulk;
            lastBulk = null;
            return bulk;
        }
    }

    private Map<String, ?> diffResult(Map<String, String> tickets) {
        var result = new HashMap<String, Object>();
        result.put("mode", "diff");
        result.put("tickets", tickets);
        result.put("key", "test");
        return result;
    }

    private Map<String, ?> addResult(Map<String, String> tickets) {
        var result = new HashMap<String, Object>();
        result.put("mode", "add");
        result.put("tickets", tickets);
        result.put("key", "test");
        return result;
    }

    public Map<String, String> checkResult(Integer... tickets) {
        var response = new ArrayTable(
                List.of("key", "msg"),
                Collections.map(tickets, t -> List.of("key"+t, "msg"+t))
        ).toHtml();

        return Map.of("type", "html", "result", response);
    }

    @Test
    public void testTask() {
        var router = new MockRouterClient();
        var task = new CheckTask("task", "*/1 * * * 1-5", null, "command", "test:${key}", null, "${msg}", router, 1, 2, 100);

        // no issues
        router.nextResponse = Map.of("type", "text", "result", "[]");
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Collections.emptyMap()), router.take());

        // failure 1
        router.nextResponse = checkResult(1, 2);
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Collections.emptyMap()), router.take());

        // failure 2
        router.nextResponse = checkResult(1, 2);
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Collections.emptyMap()), router.take());

        // raise on failure 3
        router.nextResponse = checkResult(1, 2);
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Map.of("test:key1", "msg1", "test:key2", "msg2")), router.take());

        // raise on failure 4, new key
        router.nextResponse = checkResult(2, 3);
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Map.of("test:key2", "msg2")), router.take());

        // first run failure
        router.nextException = new Exception("test");
        task.run(LocalDateTime.now());
        assertNull(router.take());

        // run failure 2
        router.nextException = new Exception("test");
        task.run(LocalDateTime.now());
        assertEquals(addResult(Map.of("test", "Problem running [task]: java.lang.Excepti_n: test")), router.take());

        // back to normal
        router.nextResponse = checkResult(2, 3);
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Map.of( "test:key2", "msg2")), router.take());

        // but didn't forget about 3
        router.nextResponse = checkResult(1, 3);
        task.run(LocalDateTime.now());
        assertEquals(diffResult(Map.of( "test:key3", "msg3")), router.take());
    }
}
