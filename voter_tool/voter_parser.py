import re

def parse_voter_lines(lines, booth_name):
    """
    Parse a list of text lines into a list of voter dictionaries.
    Each voter dict contains: Booth, Name, Father_Husband, House, Age, Gender, EPIC.
    """
    voters = []
    current = {}

    for line in lines:
        # Start of a new voter
        if re.match(r'^नाम\s*[:]', line):
            if current.get('Name') and current.get('Age') and current.get('House'):
                voters.append(current.copy())
            name_raw = re.sub(r'^नाम\s*[:]\s*', '', line).strip()
            name_raw = re.split(r'\s+नाम\s*:', name_raw)[0].strip()
            current = {'Booth': booth_name, 'Name': name_raw}
            continue

        # Father/Husband name
        if re.search(r'(पिता का नाम|पति का नाम)', line) and current:
            father_raw = re.sub(r'(पिता का नाम|पति का नाम)\s*[:]\s*', '', line).strip()
            father_raw = re.split(r'\s+(पिता|पति)\s+का\s+नाम', father_raw)[0].strip()
            current['Father_Husband'] = father_raw

        # House number
        if re.search(r'मकान संख्या', line) and current:
            house_raw = re.sub(r'मकान संख्या\s*[:]\s*', '', line).strip()
            house_token = re.match(r'[\w/]+', house_raw)
            current['House'] = house_token.group(0) if house_token else house_raw

        # Age and Gender (may be on same line)
        if re.search(r'आयु\s*[:]', line) and current:
            age = re.search(r'आयु\s*[:]\s*(\d+)', line)
            gender = re.search(r'(महिला|पुरुष)', line)
            if age:
                current['Age'] = age.group(1)
            if gender:
                current['Gender'] = gender.group(1)

        # EPIC number (alphanumeric, 8+ chars)
        if re.search(r'[A-Z0-9]{8,}', line) and current and len(line) < 40:
            current['EPIC'] = re.search(r'[A-Z0-9]{8,}', line).group(0)

    # Add the last voter if complete
    if current.get('Name') and current.get('Age') and current.get('House'):
        voters.append(current.copy())

    return voters