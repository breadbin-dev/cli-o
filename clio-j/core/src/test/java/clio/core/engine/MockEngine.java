package clio.core.engine;

import clio.core.Executor;
import clio.core.Subscription;

public class MockEngine extends Engine<MockTick> {

    private final HashMapInput<String, MockObj> mapInput = new HashMapInput<>();
    private final LinkedListInput<Double> listInput = new LinkedListInput<>();
    private final LastInput<String> lastInput = new LastInput<>();

    private final Subscription<MockTick> output;

    public MockEngine(Executor executor, String execKey, Subscription<MockTick> output) {
        super(executor, execKey);
        this.output = output;
    }

    public void onObj(MockObj obj) {
        this.input(obj.name(), obj, mapInput, true);
    }

    public void onDouble(Double d) {
        this.input(d, listInput, true);
    }

    public void onStr(String str) {
        this.input(str, lastInput, false);
    }

    @Override
    protected MockTick tick(long seq) {
        return new MockTick(seq, mapInput.tick(), listInput.tick(), lastInput.tick());
    }

    @Override
    protected void execute(long seq, MockTick tick) {
        if (seq != tick.seq())
            throw new RuntimeException("Sequence doesn't match");
        output.accept(null, tick);
    }
}
