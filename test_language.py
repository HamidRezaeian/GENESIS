from genesis_engine import DynamicBrain
import random

def test_true_differentiable_communication():
    # A senses hazard, emits signal.
    # B receives signal, defends. B's loss gradient w.r.t signal is passed back to A.
    brainA = DynamicBrain(input_size=2, output_size=2, hidden_size=2)
    brainB = DynamicBrain(input_size=2, output_size=2, hidden_size=2)
    
    lr = 0.05
    success_rate = 0
    
    for epoch in range(10000): # Might take longer to converge without direct supervision
        hazard_present = random.choice([True, False])
        a_sense = 1.0 if hazard_present else 0.0
        
        # A forward
        a_out, a_ctx = brainA.predict([a_sense, 0.0])
        a_signal = a_out[1]
        
        # B forward
        b_out, b_ctx = brainB.predict([0.0, a_signal])
        b_defend = b_out[0]
        
        target_defend = 1.0 if hazard_present else 0.0
        
        # B loss and backprop
        b_err_defend = b_defend - target_defend
        b_grad_x = brainB.learn(lr, [b_err_defend, 0.0], b_ctx)
        
        # B's gradient w.r.t its second input (a_signal)
        dl_dsig = b_grad_x[1]
        
        # A backprop using B's gradient
        # A's own defend doesn't matter for this test, so 0.0 error
        brainA.learn(lr, [0.0, dl_dsig], a_ctx)
        
        if abs(b_err_defend) < 0.2:
            success_rate += 1
            
        if epoch % 1000 == 0:
            print(f"Epoch {epoch} | Hazard: {hazard_present} | A sig: {a_signal:.2f} | B def: {b_defend:.2f} | Error: {abs(b_err_defend):.2f}")

    final_success = (success_rate / 10000.0) * 100.0
    print(f"Final Success Rate: {final_success:.1f}%")
    if final_success > 90.0:
        print("SUCCESS: Differentiable Communication solved Symbol Grounding!")
    else:
        print("FAILURE: Multi-Agent Backprop did not converge.")

if __name__ == '__main__':
    test_true_differentiable_communication()
