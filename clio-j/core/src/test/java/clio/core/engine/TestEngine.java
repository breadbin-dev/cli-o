package clio.core.engine;

import clio.core.MockExecutor;
import clio.core.Subscription;
import org.junit.Test;

import java.util.LinkedList;

import static org.junit.Assert.assertEquals;

public class TestEngine {

    @Test
    public void testEngine() {
        var results = new LinkedList<MockTick>();
        var errs = new LinkedList<String>();

        var output = new Subscription<MockTick>() {

            @Override
            public void onError(String key, String msg) {
                errs.add(msg);
            }

            @Override
            public void accept(String key, MockTick value) {
                results.add(value);
            }
        };

        var executor = new MockExecutor();
        var engine = new MockEngine(executor, "key", output);

        // test if update delayed then single exec gets latest value

        engine.onObj(new MockObj("A", 1));
        assertEquals(1, executor.tasks.size());

        engine.onObj(new MockObj("A", 2));
        engine.onObj(new MockObj("A", 3));
        assertEquals(1, executor.tasks.size());

        executor.tasks.remove().run();
        assertEquals(1, results.size());
        var result = results.remove();
        assertEquals(1, result.mapInputs().size());
        assertEquals(3, result.mapInputs().get("A").value());
    }
}
