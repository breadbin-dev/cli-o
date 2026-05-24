package clio.core;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.function.Supplier;

import static clio.core.Strings.f;

public class ConsoleCommand implements Runnable {
    public static ConsoleCommand of(String command, String log, LocalDateTime schedule, String name) {
        return new ConsoleCommand(command, () -> log, schedule, name);
    }
    public static ConsoleCommand of(String command, String name) {
        return new ConsoleCommand(command, (Supplier<String>)null, LocalDateTime.now(), name);
    }

    public static ConsoleCommand of(String command, String log, String name) {
        return new ConsoleCommand(command, () -> log, LocalDateTime.now(), name);
    }

    public static ConsoleCommand of(String command, Supplier<String> logs, String name) {
        return new ConsoleCommand(command, logs, LocalDateTime.now(), name);
    }

    private final String command;
    private final Supplier<String> logFile;
    private final LocalDateTime schedule;
    private final String name;

    public ConsoleCommand(String command, Supplier<String> logFile, LocalDateTime schedule, String name) {
        this.command = command;
        this.logFile = logFile;
        this.schedule = schedule != null ? schedule : LocalDateTime.now();
        this.name = name;
    }

    @Override
    public void run() {
        try {
            var processBuilder = new ProcessBuilder(Strings.splitBySpaces(command));
            if (logFile != null) {
                setupLogging(processBuilder);
            } else {
                processBuilder.inheritIO();
            }

            var process = processBuilder.start();
            var exitCode = process.waitFor();

            if (exitCode != 0) {
                if (exitCode == 75)
                    throw new NotReady(f("Process returned NOT_READY [{}]", exitCode));

                throw new RuntimeException(f("Process exited with non-zero exit code [{}]", exitCode));
            }
        }
        catch (IOException | InterruptedException ex)
        {
            throw new RuntimeException(ex);
        }
    }

    private void setupLogging(ProcessBuilder processBuilder) throws IOException {
        processBuilder.redirectErrorStream(true);
        var logFilePath = logFile.get();
        var logFile = new File(logFilePath);

        if (!logFile.exists() && !logFile.createNewFile()) {
            throw new IOException("Failed to create log file: " + logFilePath);
        }

        processBuilder.redirectOutput(ProcessBuilder.Redirect.appendTo(logFile));

        try (var logWriter = new FileWriter(logFile, true)) {
            logWriter.write("\n\n-- Process: " + this.name + " " + Dttms.formatDttm(schedule) + " --\n");
        }
    }
}