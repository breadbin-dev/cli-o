package clio.core;

import clio.core.db.*;
import clio.core.router.RouterClient;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.*;
import java.util.regex.Pattern;

import static clio.core.Strings.f;

public class Application {

    private static final Logger log = LogManager.getLogger(Application.class);

    private final Map<Class<?>, Object> services = new HashMap<>();
    private final Properties properties = new Properties();

    private final List<Component> components;

    public Application(Component... components) {
        this.components = new ArrayList<>(Arrays.asList(components));
        properties.putAll(System.getenv()); // added once to be available for variable replacement
        addPropertiesFile("environment.properties", new HashSet<>());
        properties.putAll(System.getenv());  // added again to override variables from files
    }

    public void addComponents(Component... components) {
        this.components.addAll(Arrays.asList(components));
    }

    public void addComponent(int index, Component component) {
        this.components.add(index, component);
    }

    public String env() {
        return ensureProperty("env");
    }

    private InputStream find(String resource) throws FileNotFoundException {
        if (Files.exists(Paths.get(resource)))
            return new FileInputStream(resource);
        else
            return Application.class.getClassLoader().getResourceAsStream(resource);
    }

    private void addPropertiesFile(String resource, Set<String> seen) {
        try (var stream = find(resource)) {
            seen.add(resource);
            properties.load(stream);
        } catch (Exception ex) {
            throw new RuntimeException(f("problem loading resource [{}]", resource), ex);
        }

        var imports = getProperties("^import\\..*");
        for (var prop : imports.keySet().stream().sorted().toList()) {
            var file = imports.get(prop);
            if (!seen.contains(file)) {
                addPropertiesFile(file, seen);
            }
        }
    }

    public void run() {
        run(true);
    }

    public void run(boolean awaitShutdown) {
        for (var component : components) {
            try {
                log.info("Starting component: {}...", component.getClass().getName());
                component.start(this);
            }
            catch (Exception ex) {
                log.error("Problem starting component: {}", component.getClass().getName(), ex);
                System.exit(1);
            }
        }

        if (awaitShutdown)
            new ShutdownHook().await(this::shutdown);
        else
            shutdown();
    }

    private void shutdown() {
        for (var component : components) {
            try {
                component.prepareShutdown();
            }
            catch (Exception ex) {
                log.error("Problem preparing shutdown component: {}", component.getClass().getName(), ex);
            }
        }

        for (var component : Collections.reverse(components)) {
            try {
                log.info("Stopping component: {}...", component.getClass().getName());
                component.stop();
            } catch (Exception ex) {
                ex.printStackTrace();
                log.error("Problem stopping component: {}", component.getClass().getName(), ex);
            }
        }
        LogManager.shutdown();
    }

    public <T> void addService(T service) {
        addService(service, (Class<T>)service.getClass());
    }

    public <T> void addService(T service, Class<T> clz) {
        services.put(clz, service);
    }

    public <T> T getService(Class<T> clz) {
        return (T)services.get(clz);
    }

    public <T> T ensureService(Class<T> clz) {
        var service = getService(clz);
        if (service == null)
            throw new RuntimeException("No service found for " + clz);
        return service;
    }

    public String getProperty(String property) {
        return getProperty(property, (String)null);
    }

    public <T> T getProperty(String property, Class<T> clz) {
        var value = getProperty(property);
        return value == null ? null : Strings.parse(value, clz);
    }

    public String getProperty(String property, String dflt) {
        var prop = properties.getProperty(property, dflt);
        return prop == null ? null : Strings.replaceVariables(prop, this::ensureProperty);
    }

    public String ensureProperty(String property) {
        var prop = getProperty(property);
        if (prop == null)
            throw new RuntimeException("No property found for " + property);
        return prop;
    }

    public <T> T ensureProperty(String property, Class<T> clz) {
        return Strings.parse(ensureProperty(property), clz);
    }

    public Map<String, String> getProperties(String pattern) {
        var regex = Pattern.compile(pattern);
        var result = new HashMap<String, String>();
        for (var key : (Set<String>)(Set<?>)properties.keySet()) {
            if (regex.matcher(key).find())
                result.put(key, getProperty(key));
        }
        return result;
    }

    public Map<String, String> getChildProperties(String prefix) {
        var result = new HashMap<String, String>();
        for (var key : (Set<String>)(Set<?>)properties.keySet()) {
            if (key.startsWith(prefix))
                result.put(key.substring(prefix.length()), getProperty(key));
        }
        return result;
    }

    public <T> Map<String, T> getChildProperties(String prefix, Class<T> cls) {
        var result = new HashMap<String, T>();
        for (var key : (Set<String>)(Set<?>)properties.keySet()) {
            if (key.startsWith(prefix))
                result.put(key.substring(prefix.length()), Strings.parse(getProperty(key), cls));
        }
        return result;
    }

    public Database getDatabase(String name, JdbcAdapter<?>... adapters) {
        try {
            var config = getChildProperties(name + "_");
            var url = Collections.ensure(config, "url");
            var username = Collections.ensure(config, "username");
            var password = Collections.ensure(config, "password");

            Syntax syntax;
            if (url.startsWith("jdbc:sqlite"))
                syntax = new SQLiteSyntax();
            else if (url.startsWith("jdbc:clickhouse"))
                syntax = new ClickhouseSyntax();
            else
                throw new RuntimeException("Unknown connection type: " +url);

            var conn = DriverManager.getConnection(url, username, password);
            return new Database(conn, syntax, adapters);
        }
        catch (SQLException ex) {
            throw new RuntimeException(ex);
        }
    }

    public RouterClient getRouterClient() {
        return new RouterClient(ensureProperty("router_url"), ensureProperty("router_token"));
    }

    public InputStream ensurePropertyResource(String property) {
        try {
            return find(ensureProperty(property));
        } catch (FileNotFoundException e) {
            throw new RuntimeException(e);
        }
    }

    public static boolean isServiceUser(String user) {
        return Strings.hasValue(user) && user.startsWith("svc_");
    }
}
