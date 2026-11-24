import org.junit.runner.JUnitCore;
import org.junit.runner.Request;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;

/** Runs one JUnit 3 or 4 test method. Exit 0 = pass, 1 = fail, 2 = could not run. */
public class SingleTest {
    public static void main(String[] args) throws Exception {
        String[] parts = args[0].split("::");
        Class<?> cls;
        try {
            cls = Class.forName(parts[0]);
        } catch (Throwable t) {
            System.out.println("RESULT ERROR class not found: " + parts[0]);
            System.exit(2);
            return;
        }
        Request req = parts.length > 1 ? Request.method(cls, parts[1]) : Request.aClass(cls);
        Result r = new JUnitCore().run(req);
        for (Failure f : r.getFailures()) {
            System.out.println("FAILURE " + f.getTestHeader() + ": " + f.getMessage());
        }
        if (r.getRunCount() == 0) {
            System.out.println("RESULT ERROR no test ran");
            System.exit(2);
        }
        System.out.println("RESULT " + (r.wasSuccessful() ? "PASS" : "FAIL") + " run=" + r.getRunCount());
        System.exit(r.wasSuccessful() ? 0 : 1);
    }
}
