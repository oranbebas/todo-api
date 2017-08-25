CREATE TABLE task (
  id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  done BOOLEAN NOT NULL DEFAULT False
);

INSERT INTO task VALUES (
  1,'Buy groceries','Milk, Cheese, Pizza, Fruit, Tylenol',False
), (
  2,'Learn Python','Neet to find a good Python tutorial on the web',False
);
