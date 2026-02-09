# salon/utils.py

def calculate_commission(appointment):
    """
    Calculate commission for ONE completed appointment
    """
    service_price = appointment.service.price
    commission_percent = appointment.staff.commission

    commission = (service_price * commission_percent) / 100
    return commission
