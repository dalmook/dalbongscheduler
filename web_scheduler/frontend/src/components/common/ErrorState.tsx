function ErrorState({ message }: { message: string }) {
  return <div className="state error">Error: {message}</div>;
}

export default ErrorState;
