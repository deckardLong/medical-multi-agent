from product.db.models import Family, FamilyMember, User

# Check whether it's owner
def is_owner(family: Family, user: User) -> bool:
    return family.owner_user_id == user.id

# Check permission to write
def can_write_member(member: FamilyMember, family: Family, user: User) -> bool:
    # If there is no account (other member in the family like baby, old people,...) => They will be mananged by owner
    if member.linked_user_id is None:
        return is_owner(family, user)
    return member.linked_user_id == user.id
