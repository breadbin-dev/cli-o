package clio.core;

public class Exceptions {
    public static String msg(Throwable ex) {
        return msg(ex, 300);
    }

    public static String msg(Throwable ex, int maxLength) {
        var msg = ex.getMessage();
        if (msg == null || msg.isBlank())
            msg = ex.getClass().getSimpleName();
        else if (msg.length() > maxLength)
            msg = msg.substring(0, maxLength) + "...";
        return msg;
    }

    public static String cleanMessage(Throwable ex) {
        return cleanMessage(ex, 300);
    }

    public static String cleanMessage(Throwable ex, int maxLength) {
        return cleanMessage(Exceptions.msg(ex, maxLength));
    }

    public static String cleanMessage(String msg) {
        return msg
                .replace("error", "err_r")
                .replace("exception", "excepti_n")
                .replace("fatal", "fat_l")
                .replace("Error", "Err_r")
                .replace("Exception", "Excepti_n")
                .replace("Fatal", "Fat_l")
                .replace("ERROR", "ERR_R")
                .replace("EXCEPTION", "EXCEPTI_N")
                .replace("FATAL", "FAT_L");
    }
}
