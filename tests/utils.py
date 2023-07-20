from time import sleep


class CommandContext:
    def __init__(self, client, chat_id, command, logger):
        self.client = client
        self.chat_id = chat_id
        self.command = command
        self.logger = logger
        self.step = 1


    def __enter__(self):
        self.message = self.client.send_message(chat_id=self.chat_id, text=self.command)
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.exception(f"'{self.command}' failed due to exception on step {self.step}\n"
                                  f"{exc_type} {exc_val} {exc_tb}")
    

    def expect_next(self, correct_response, sleep_s=0.2, timeout_s=2):
        assert correct_response is not None, "correct_response should be specified"
        
        timer = 0
        while timer < timeout_s:
            response = self.client.get_messages(self.chat_id, self.message.id + self.step).text
            if response is not None: # found target message
                self.step += 1
                if response == correct_response:
                    self.logger.info(f"'{self.command}' step {self.step - 1} passed successfuly!")
                    return True
                
                self.logger.info(f"'{self.command}' failed due to wrong reaction on step {self.step - 1}"
                                 f"\nreaction: {response}\nexpected: {correct_response}")
                return False
            timer += sleep_s
            sleep(sleep_s)
        self.logger.info(f"'{self.command}' failed due to absence of reaction on step {self.step}")
        return False

 
    def expect_next_prefix(self, correct_response_prefix, sleep_s=0.2, timeout_s=2):
        assert correct_response_prefix is not None, "correct_response should be specified"
        
        timer = 0
        while timer < timeout_s:
            response = self.client.get_messages(self.chat_id, self.message.id + self.step).text
            if response is not None: # found target message
                self.step += 1
                if response.startswith(correct_response_prefix):
                    self.logger.info(f"'{self.command}' step {self.step - 1} passed successfuly!")
                    return True
                
                self.logger.info(f"'{self.command}' failed due to wrong reaction on step {self.step - 1}"
                                 f"\nreaction: {response}\nexpected prefix: {correct_response_prefix}")
                return False
            timer += sleep_s
            sleep(sleep_s)
        self.logger.info(f"'{self.command}' failed due to absence of reaction on step {self.step}")
        return False


    def expect_none(self, sleep_s=0.5, timeout_s=2):
        timer = 0
        while timer <= timeout_s:
            response = self.client.get_messages(self.chat_id, self.message.id + self.step).text
            if response is not None: # found target message
                self.logger.info(f"'{self.command}' failed due to presence of reaction on step {self.step}",
                                 f"\nreaction: {response}")
                return False
            
            timer += sleep_s
            sleep(sleep_s)
        
        self.logger.info(f"'{self.command}' step {self.step} passed successfuly!")
        return True
    
    
    def expect_length(self, num_rows, sleep_s=0.5, timeout_s=2):
        raise NotImplementedError
