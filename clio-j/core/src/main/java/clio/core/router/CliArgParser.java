package clio.core.router;

import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.DefaultParser;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;

import java.util.HashMap;
import java.util.Map;

import static clio.core.Strings.f;
import static clio.core.Strings.splitWithQuotes;

public class CliArgParser implements ArgParser<Map<String, Object>> {

    public record Option(String opt, String longOpt, String type, String description, boolean isList) {
        public String toString() {
            var t = isList ? "list[" + this.type + "]" : "[" + this.type + "]";
            if (opt == null)
                return f("--{} {}: {}", longOpt, t, description);
            else
                return f("-{} --{} {}: {}", opt, longOpt, t, description);
        }
    }

    public static CliArgParser of(CliArgParser.Option... options) {
        if (options.length == 0)
            return null;

        return new CliArgParser(options);
    }

    private final CliArgParser.Option[] options;
    private final CommandLineParser parser;
    private final Options parserOptions;

    public CliArgParser(CliArgParser.Option... options) {
        this.parser = new DefaultParser();
        this.options = options;
        this.parserOptions = new Options();

        for (var opt : options) {
            var b = org.apache.commons.cli.Option.builder();
            b.longOpt(opt.longOpt).desc(opt.description);

            if (opt.opt != null) {
                b.option(opt.opt);
            }
            if (opt.type.equals("boolean")) {
                this.parserOptions.addOption(b.hasArg(false).build());
            } else if (opt.isList) {
                this.parserOptions.addOption(b.hasArgs().build());
            } else {
                this.parserOptions.addOption(b.hasArg(true).build());
            }
        }
    }

    @Override
    public Map<String, Object> parse(String args) {
        try {
            var parsed = parser.parse(parserOptions, splitWithQuotes(args));
            var result = new HashMap<String, Object>();
            for (var option : options) {
                if (parsed.hasOption(option.longOpt)) {
                    if (option.type.equals("boolean")) {
                        result.put(option.longOpt, true);
                    } else if (option.isList) {
                        result.put(option.longOpt, parsed.getOptionValues(option.longOpt));
                    } else {
                        result.put(option.longOpt, parsed.getOptionValue(option.longOpt));
                    }
                } else if (option.type.equals("boolean")) {
                    result.put(option.longOpt, false);
                }
            }
            return result;
        } catch(ParseException ex) {
            throw new RuntimeException(ex);
        }
    }
}
