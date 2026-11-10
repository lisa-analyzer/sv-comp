import org.sosy_lab.sv_benchmarks.Verifier;

public class Main {
  public static void main(String[] args) {
    int x = Verifier.nondetInt();
    int s = 0;
    for (int i = 0; i < 1000; i++)
      s += i;
    if (x == s) {
      assert false;
    }
  }
}
