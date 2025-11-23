// Go HTTP server
package main

import (
	"log"
	"net/http"
)

type Server struct {
	Port string
	Mux  *http.ServeMux
}

func NewServer(port string) *Server {
	return &Server{
		Port: port,
		Mux:  http.NewServeMux(),
	}
}

func (s *Server) Start() error {
	log.Printf("Starting server on port %s", s.Port)
	return http.ListenAndServe(":"+s.Port, s.Mux)
}
