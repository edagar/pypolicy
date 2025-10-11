
# func def
def f(x)
    return x * 2
end

# list construction and assignment
l = [1,2]

# bound methods
print(l.map(f))


# if stmt
def test_if_else(x)
    if x == "root"
        print("greetings, allmighty root")
    elif x == "admin"
        print("hi there, mr admin")
    else
        print("hello, humble user")
    end
    return nil
end

# for loop
for n in ["user", "root"]:
    test_if_else(n)
end

# dicts
user = {"name": "alice"}
user["age"] := 38
print(user)

token["roles"]["client_b"] := [1,2,3]
print(token)

# range objects - wrapped python objects and bound methods

for x in range(10):
    print(x)
end

# single-expression lambdas

print([1, 2, 3].map(i => i * i))


# multi statement lambdas

g = (a, b) =>
    print(a)
    print(b)
    return a + b
end

print(g(10, 20))


# and / or
print("=========")
print(true or false)
print(true and true)
print(true and false)
print(true and false)
print(true and false)


if false or true
    print("works!")
end

if true and true
    print("also works!")
end

if true and false
    print("never reached")
elif false or true
    print("reached")
end

print("=========")

# policy return value
return i in l

