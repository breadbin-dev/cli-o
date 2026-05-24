package clio.core.router;

import clio.core.Disposable;
import clio.core.Strings;
import clio.core.Subscription;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.function.Supplier;

import static clio.core.Strings.f;

public class Confirms implements Subscription<RouterHost.Call<Map<String, Object>>> {

    private static final Logger log = LoggerFactory.getLogger(Confirms.class);

    public class Prompt implements Disposable {

        private final LinkedHashMap<String, Consumer<RouterHost.Call<?>>> actions = new LinkedHashMap<>();

        private final String prompt;
        private final String id;

        public Prompt(String prompt, String id) {
            this.prompt = prompt;
            this.id = id;
        }

        public void add(String option, Consumer<RouterHost.Call<?>> action) {
            actions.put(option, action);
        }

        public void respond(RouterHost.Call<?> call) {
            var options = new LinkedHashMap<String, Object>();
            for (var action : actions.keySet()) {
                options.put(action, f("{} -i {} -a {}", responseCommand, id, action));
            }

            var confirm = new LinkedHashMap<String, Object>();
            confirm.put("prompt", prompt);
            confirm.put("options", options);

            call.respond("confirm", confirm);
        }

        @Override
        public void close() {
            prompts.remove(id);
        }
    }

    private final Supplier<String> uniqueCounter = Strings.uniqueCounter();
    private final Map<String, Prompt> prompts = new ConcurrentHashMap<>();
    private final String responseCommand;

    public Confirms(String responseCommand) {
        this.responseCommand = responseCommand;
    }

    public CliArgParser.Option[] responseOptions() {
        return new CliArgParser.Option[]{
                new CliArgParser.Option("i", "id", "str", "prompt id", false),
                new CliArgParser.Option("a", "action", "str", "user action", false)
        };
    }

    public Prompt prompt(String prompt) {
        var id = uniqueCounter.get();
        var result = new Prompt(prompt, id);
        prompts.put(id, result);
        return result;
    }

    @Override
    public void accept(String key, RouterHost.Call<Map<String, Object>> response) {
        String id = response.getArg("id");
        var prompt = prompts.remove(id);
        if (prompt == null)
            throw new RuntimeException("Prompt not found " + id);

        String userAction = response.getArg("action");
        var action = prompt.actions.get(userAction);
        if (action == null)
            throw new RuntimeException("Action not found " + userAction);

        action.accept(response);
    }

    @Override
    public void onError(String key, String msg) {
        log.error("Problem on confirm response: {}", msg);
    }
}
