import random

class DynamicBrain:
    def __init__(self, input_size, output_size, hidden_size=0):
        self.i_sz = input_size
        self.o_sz = output_size
        self.w_in = [[random.uniform(-1, 1) for _ in range(input_size)] for _ in range(hidden_size)]
        self.b_in = [random.uniform(-1, 1) for _ in range(hidden_size)]
        self.w_out = [[random.uniform(-1, 1) for _ in range(hidden_size)] for _ in range(output_size)]
        self.b_out = [random.uniform(-1, 1) for _ in range(output_size)]
        self.direct_w = [[random.uniform(-1, 1) for _ in range(input_size)] for _ in range(output_size)]
        
    def predict(self, x):
        self.last_x = x
        self.hidden_acts = []
        for i in range(len(self.w_in)):
            val = sum(x[j] * self.w_in[i][j] for j in range(self.i_sz)) + self.b_in[i]
            val = max(0.01 * val, val)
            self.hidden_acts.append(val)
            
        out = []
        for o in range(self.o_sz):
            val = sum(x[j] * self.direct_w[o][j] for j in range(self.i_sz)) + self.b_out[o]
            val += sum(self.hidden_acts[i] * self.w_out[o][i] for i in range(len(self.hidden_acts)))
            out.append(max(0.0, min(1.0, val))) # clamp output between 0 and 1
        return out
        
    def learn(self, lr, errors):
        for o in range(self.o_sz):
            err = errors[o]
            self.b_out[o] -= lr * err
            for j in range(self.i_sz):
                self.direct_w[o][j] -= lr * err * self.last_x[j]
                
            for i in range(len(self.w_out[o])):
                h_act = self.hidden_acts[i]
                self.w_out[o][i] -= lr * err * h_act
                hidden_error = err * self.w_out[o][i]
                grad = 1 if h_act > 0 else 0.01
                hidden_error *= grad
                self.b_in[i] -= lr * hidden_error
                for j in range(self.i_sz):
                    self.w_in[i][j] -= lr * hidden_error * self.last_x[j]

def test_language_emergence():
    brainA = DynamicBrain(2, 2, hidden_size=2)
    brainB = DynamicBrain(2, 2, hidden_size=2)
    
    lr = 0.05
    success_rate = 0
    
    for epoch in range(1000):
        hazard_present = random.choice([True, False])
        a_sense = 1.0 if hazard_present else 0.0
        
        a_out = brainA.predict([a_sense, 0.0])
        a_defend = a_out[0]
        a_signal = a_out[1]
        
        b_out = brainB.predict([0.0, a_signal])
        b_defend = b_out[0]
        b_signal = b_out[1]
        
        target_defend = 1.0 if hazard_present else 0.0
        
        b_err_defend = b_defend - target_defend
        b_err_signal = 0.0 
        
        a_err_defend = a_defend - target_defend
        a_err_signal = a_signal - target_defend 
        
        brainB.learn(lr, [b_err_defend, b_err_signal])
        brainA.learn(lr, [a_err_defend, a_err_signal])
        
        if abs(b_err_defend) < 0.2 and abs(a_err_defend) < 0.2:
            success_rate += 1
            
        if epoch % 100 == 0:
            print(f"Epoch {epoch} | Hazard: {hazard_present} | A sig: {a_signal:.2f} | B def: {b_defend:.2f} | Error: {abs(b_err_defend):.2f}")

    print(f"Final Success Rate (last 100): {success_rate % 100}%")

if __name__ == '__main__':
    test_language_emergence()
