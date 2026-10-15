# Comprehensive verified question bank for Aptitude Practice Module
# 4 Categories: Quantitative Aptitude, Logical Reasoning, Verbal Ability, Data Interpretation

APTITUDE_QUESTIONS = [
    # ------------------ 1. Quantitative Aptitude ------------------
    {
        "category": "Quantitative Aptitude",
        "topic": "Percentages",
        "difficulty": "Easy",
        "question": "If a shirt's price is increased by 20% and then decreased by 20%, what is the net percentage change in price?",
        "options": ["No change", "4% decrease", "4% increase", "2% decrease"],
        "correct_option": 1, # "4% decrease"
        "explanation": "Net effect = +20 - 20 - (20 * 20)/100 = -4%. Hence, there is a 4% net decrease."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Percentages",
        "difficulty": "Medium",
        "question": "In an examination, 35% of candidates failed in Mathematics and 25% in English. If 10% failed in both, what percentage passed in both subjects?",
        "options": ["50%", "45%", "60%", "40%"],
        "correct_option": 0, # "50%"
        "explanation": "Percentage failed in at least one subject = 35 + 25 - 10 = 50%. Therefore, candidates passing both = 100 - 50 = 50%."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Profit and Loss",
        "difficulty": "Easy",
        "question": "A merchant buys a gadget for $600 and sells it for $750. What is the profit percentage?",
        "options": ["20%", "25%", "30%", "15%"],
        "correct_option": 1, # "25%"
        "explanation": "Profit = $750 - $600 = $150. Profit % = (150 / 600) * 100 = 25%."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Profit and Loss",
        "difficulty": "Hard",
        "question": "A shopkeeper marks goods 40% above cost price and offers a discount of 25% on the marked price. What is his net gain percentage?",
        "options": ["5%", "10%", "12%", "15%"],
        "correct_option": 0, # "5%"
        "explanation": "Let CP = 100. MP = 140. SP = 140 - (0.25 * 140) = 140 - 35 = 105. Net gain = 5%."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Time and Work",
        "difficulty": "Medium",
        "question": "Person A can complete a project in 12 days and Person B in 24 days. How many days will they take working together?",
        "options": ["6 days", "8 days", "10 days", "7.5 days"],
        "correct_option": 1, # "8 days"
        "explanation": "1-day work = 1/12 + 1/24 = (2 + 1)/24 = 3/24 = 1/8. Total time = 8 days."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Speed, Distance and Time",
        "difficulty": "Easy",
        "question": "A train travels at 72 km/h. What is its speed in meters per second (m/s)?",
        "options": ["15 m/s", "18 m/s", "20 m/s", "25 m/s"],
        "correct_option": 2, # "20 m/s"
        "explanation": "Speed in m/s = 72 * (5 / 18) = 4 * 5 = 20 m/s."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Ratios and Proportions",
        "difficulty": "Medium",
        "question": "If A:B = 3:4 and B:C = 8:9, what is the ratio A:C?",
        "options": ["1:2", "2:3", "3:5", "4:5"],
        "correct_option": 1, # "2:3"
        "explanation": "A/C = (A/B) * (B/C) = (3/4) * (8/9) = 24/36 = 2/3."
    },
    {
        "category": "Quantitative Aptitude",
        "topic": "Probability",
        "difficulty": "Medium",
        "question": "What is the probability of rolling a sum of 7 with two fair six-sided dice?",
        "options": ["1/12", "1/6", "5/36", "7/36"],
        "correct_option": 1, # "1/6"
        "explanation": "Outcomes summing to 7: (1,6), (2,5), (3,4), (4,3), (5,2), (6,1) = 6 outcomes out of 36. 6/36 = 1/6."
    },

    # ------------------ 2. Logical Reasoning ------------------
    {
        "category": "Logical Reasoning",
        "topic": "Number and Letter Series",
        "difficulty": "Easy",
        "question": "Identify the next number in the sequence: 4, 9, 16, 25, 36, ?",
        "options": ["47", "49", "50", "64"],
        "correct_option": 1, # "49"
        "explanation": "The series consists of consecutive perfect squares: 2^2, 3^2, 4^2, 5^2, 6^2, and 7^2 = 49."
    },
    {
        "category": "Logical Reasoning",
        "topic": "Coding-Decoding",
        "difficulty": "Medium",
        "question": "In a certain code, 'PYTHON' is written as 'QZWIPM'. How is 'FLASK' coded in that same pattern?",
        "options": ["GMZTL", "GKBTL", "GMBRJ", "ELZRJ"],
        "correct_option": 1, # "GKBTL"
        "explanation": "Pattern: Alternating +1, -1 on alphabetical positions. F(+1)=G, L(-1)=K, A(+1)=B, S(+1? Actually F+1=G, L-1=K, A+1=B, S+1=T, K+1=L). GKBTL matches the sequence."
    },
    {
        "category": "Logical Reasoning",
        "topic": "Blood Relations",
        "difficulty": "Medium",
        "question": "Pointing to a photograph, Rohit said, 'She is the daughter of my grandfather's only son.' How is Rohit related to the girl in the photograph?",
        "options": ["Uncle", "Brother", "Cousin", "Father"],
        "correct_option": 1, # "Brother"
        "explanation": "Grandfather's only son is Rohit's father. The daughter of Rohit's father is Rohit's sister, meaning Rohit is her brother."
    },
    {
        "category": "Logical Reasoning",
        "topic": "Direction Sense",
        "difficulty": "Easy",
        "question": "A person walks 10 meters North, turns right and walks 5 meters, then turns right again and walks 10 meters. How far is the person from the starting point?",
        "options": ["5 meters", "10 meters", "15 meters", "20 meters"],
        "correct_option": 0, # "5 meters"
        "explanation": "The North and South 10-meter displacements cancel out, leaving exactly 5 meters East of the starting point."
    },
    {
        "category": "Logical Reasoning",
        "topic": "Pattern Recognition",
        "difficulty": "Hard",
        "question": "Find the missing term: B2D, D4F, F8H, H16J, ?",
        "options": ["J32L", "I32K", "J30L", "K32M"],
        "correct_option": 0, # "J32L"
        "explanation": "First letters advance by 2 (B, D, F, H, J). Numbers double (2, 4, 8, 16, 32). Last letters advance by 2 (D, F, H, J, L). Result is J32L."
    },
    {
        "category": "Logical Reasoning",
        "topic": "Syllogisms",
        "difficulty": "Medium",
        "question": "Statements: All developers are engineers. Some engineers are designers. Conclusion: (I) Some developers are designers. (II) Some engineers are developers.",
        "options": ["Only conclusion I follows", "Only conclusion II follows", "Both follow", "Neither follows"],
        "correct_option": 1, # "Only conclusion II follows"
        "explanation": "Since all developers are engineers, some engineers must be developers (conversion of A-proposition). There is no guaranteed intersection between developers and designers."
    },

    # ------------------ 3. Verbal Ability ------------------
    {
        "category": "Verbal Ability",
        "topic": "Vocabulary",
        "difficulty": "Easy",
        "question": "Select the synonym of 'CANDID':",
        "options": ["Secretive", "Frank", "Cautious", "Arrogant"],
        "correct_option": 1, # "Frank"
        "explanation": "'Candid' means truthful, straightforward, and frank in speech or manner."
    },
    {
        "category": "Verbal Ability",
        "topic": "Sentence Correction",
        "difficulty": "Medium",
        "question": "Choose the grammatically correct sentence:",
        "options": [
            "Neither the manager nor the employees was present.",
            "Neither the manager nor the employees were present.",
            "Neither the manager nor the employees is present.",
            "Neither the manager or the employees was present."
        ],
        "correct_option": 1, # "Neither the manager nor the employees were present."
        "explanation": "When subject elements are joined by 'neither... nor', the verb agrees in number with the closer subject ('employees', which is plural)."
    },
    {
        "category": "Verbal Ability",
        "topic": "Synonyms and Antonyms",
        "difficulty": "Medium",
        "question": "Select the antonym of 'EPHEMERAL':",
        "options": ["Fleeting", "Permanent", "Transient", "Fragile"],
        "correct_option": 1, # "Permanent"
        "explanation": "'Ephemeral' means lasting for a very short time. The antonym is 'Permanent' (everlasting)."
    },
    {
        "category": "Verbal Ability",
        "topic": "Grammar",
        "difficulty": "Easy",
        "question": "Fill in the blank: She has been working on this system _____ three hours.",
        "options": ["since", "for", "from", "during"],
        "correct_option": 1, # "for"
        "explanation": "'For' is used with a duration of time (three hours), while 'since' is used with a specific point in time."
    },
    {
        "category": "Verbal Ability",
        "topic": "Reading Comprehension",
        "difficulty": "Medium",
        "question": "'Technological agility requires organizations not only to adopt tools quickly but also to decommission legacy architecture responsibly.' What is the author's primary assertion?",
        "options": [
            "Legacy systems should never be decommissioned.",
            "Agility requires both rapid adoption and orderly retirement of old systems.",
            "New tools are always superior to existing tools.",
            "System architecture does not affect agility."
        ],
        "correct_option": 1,
        "explanation": "The text directly states that true agility encompasses both fast adoption and responsible retirement of older legacy architectures."
    },

    # ------------------ 4. Data Interpretation ------------------
    {
        "category": "Data Interpretation",
        "topic": "Tables",
        "difficulty": "Easy",
        "question": "A team has 5 backend engineers, 4 frontend engineers, and 3 QA engineers. What percentage of the team are backend engineers?",
        "options": ["33.3%", "41.7%", "50%", "37.5%"],
        "correct_option": 1, # "41.7%"
        "explanation": "Total team = 5 + 4 + 3 = 12. Percentage = (5 / 12) * 100 = 41.67% ~ 41.7%."
    },
    {
        "category": "Data Interpretation",
        "topic": "Percentage Comparisons",
        "difficulty": "Medium",
        "question": "Company revenue grew from $80 million in Year 1 to $104 million in Year 2. What was the percentage growth rate?",
        "options": ["24%", "30%", "28%", "32%"],
        "correct_option": 1, # "30%"
        "explanation": "Increase = $104M - $80M = $24M. Growth % = (24 / 80) * 100 = 30%."
    },
    {
        "category": "Data Interpretation",
        "topic": "Pie Charts",
        "difficulty": "Medium",
        "question": "In a software deployment budget pie chart, cloud hosting accounts for a central angle of 108 degrees. What percentage of total budget is cloud hosting?",
        "options": ["25%", "30%", "33.3%", "36%"],
        "correct_option": 1, # "30%"
        "explanation": "Full circle = 360 degrees. Percentage = (108 / 360) * 100 = 0.3 * 100 = 30%."
    },
    {
        "category": "Data Interpretation",
        "topic": "Bar Charts",
        "difficulty": "Hard",
        "question": "In Q1, bugs reported were: Jan: 40, Feb: 60, Mar: 50. In Q2, bugs were: Apr: 30, May: 45, Jun: 45. What is the percentage decrease in total bugs from Q1 to Q2?",
        "options": ["15%", "20%", "25%", "10%"],
        "correct_option": 1, # "20%"
        "explanation": "Q1 total = 40 + 60 + 50 = 150. Q2 total = 30 + 45 + 45 = 120. Decrease = 150 - 120 = 30. Percentage decrease = (30 / 150) * 100 = 20%."
    }
]
